"""AI draft generation: confidence blend, intent/confidence coercion, and the
structured-output parse paths (valid / malformed / empty draft)."""

import pytest

import backend.services.ai_service as ai
from backend.models.enums import Intent


class FakeChunk:
    content = "Refund policy: 30 days."


class FakeMsg:
    id = 5
    ticket_id = 2
    company_id = 1
    body = "Where is my refund?"


def test_confidence_no_chunks_caps_low():
    assert ai.calculate_confidence([], "anything", 90) == 15
    assert ai.calculate_confidence([], "anything", 5) == 5


def test_confidence_blends_retrieval_and_self_rating():
    chunks = [(FakeChunk(), 0.1)]  # similarity 0.9 -> retrieval 90
    # 0.7*90 + 0.3*80 = 87
    assert ai.calculate_confidence(chunks, "here you go", 80) == 87


def test_confidence_halved_on_fallback_phrase():
    chunks = [(FakeChunk(), 0.1)]
    assert ai.calculate_confidence(chunks, "I could not find that record", 80) == 43


def test_validate_intent():
    assert ai._validate_intent("refund_request") == "refund_request"
    assert ai._validate_intent("bogus") == Intent.GENERAL_SUPPORT.value
    assert ai._validate_intent(None) == Intent.GENERAL_SUPPORT.value


def test_coerce_confidence():
    assert ai._coerce_confidence("77") == 77
    assert ai._coerce_confidence(200) == 100
    assert ai._coerce_confidence("abc") == 0


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Stub retrieval + memory so generate_draft needs no DB or network."""
    monkeypatch.setattr(
        ai.rag_service, "retrieve", lambda db, q, cid: [(FakeChunk(), 0.15)]
    )
    monkeypatch.setattr(
        ai, "build_memory", lambda db, msg: "Current customer email:\n" + msg.body
    )

    def set_llm(payload):
        class FakeClient:
            def generate_structured(self, prompt):
                return payload

        monkeypatch.setattr(ai, "get_llm_client", lambda: FakeClient())

    return set_llm


def test_generate_draft_valid(stub_pipeline):
    stub_pipeline(
        '{"intent":"refund_request","confidence":80,"needs_human":false,'
        '"draft":"Dear Customer, your refund is processing."}'
    )
    out = ai.generate_draft(None, FakeMsg())
    assert out["intent"] == "refund_request"
    assert out["needs_human"] is False
    assert out["reply"].startswith("Dear Customer")
    assert out["confidence"] == 83  # 0.7*85 + 0.3*80


def test_generate_draft_malformed_defers(stub_pipeline):
    stub_pipeline("not valid json {oops")
    out = ai.generate_draft(None, FakeMsg())
    assert out["reply"] == ""
    assert out["needs_human"] is True
    assert out["confidence"] == 0
    assert out["intent"] == Intent.GENERAL_SUPPORT.value


def test_generate_draft_empty_draft_forces_human(stub_pipeline):
    stub_pipeline(
        '{"intent":"complaint","confidence":90,"needs_human":false,"draft":""}'
    )
    out = ai.generate_draft(None, FakeMsg())
    assert out["reply"] == ""
    assert out["needs_human"] is True
    assert out["confidence"] == 0
    assert out["intent"] == "complaint"
