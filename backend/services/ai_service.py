"""AI draft generation for inbound Messages — RAG retrieval + LLM + a
retrieval-grounded confidence score. Persistence is handled by ticket_service.
"""

import logging

from sqlalchemy.orm import Session

from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt
from backend.models.enums import MessageDirection
from backend.models.kb_chunk import KbChunk
from backend.models.message import Message
from backend.services import rag_service

logger = logging.getLogger(__name__)


def calculate_confidence(
    chunks: list[tuple[KbChunk, float]], response: str
) -> int:
    """Confidence 0-100, grounded in retrieval similarity.

    The dominant signal is how closely the knowledge base matched the query —
    a reply the KB cannot support must not score high. A light response check
    catches explicit non-answers. (The LLM's own self-rating is added by the
    structured generation call in Phase 5.)
    """
    if not chunks:
        return 10  # nothing retrieved — the KB has no answer for this query

    # pgvector cosine_distance is in [0, 2]; similarity = 1 - distance.
    top_distance = chunks[0][1]
    similarity = max(0.0, min(1.0, 1.0 - top_distance))
    score = similarity * 90.0
    if response and "not enough information" not in response.lower():
        score += 10.0
    return int(min(score, 100.0))


def get_ticket_history(
    db: Session, ticket_id: int, before_message_id: int | None = None
) -> str:
    """Prior Messages on a Ticket, formatted as conversation history."""
    query = db.query(Message).filter(Message.ticket_id == ticket_id)
    if before_message_id is not None:
        query = query.filter(Message.id < before_message_id)

    lines = []
    for m in query.order_by(Message.id.asc()).all():
        speaker = (
            "Customer" if m.direction == MessageDirection.INBOUND else "Support"
        )
        lines.append(f"{speaker}: {m.body}")
    return "\n".join(lines)


def generate_draft(db: Session, message: Message) -> dict:
    """Generate an AI draft reply for an inbound Message.

    Returns ``{"reply": str, "confidence": int}``. Persistence is the caller's
    job — see ``ticket_service.record_ai_draft``.
    """
    chunks = rag_service.retrieve(db, message.body, message.company_id)
    context = "\n".join(chunk.content for chunk, _distance in chunks)
    history = get_ticket_history(
        db, message.ticket_id, before_message_id=message.id
    )

    full_input = (
        f"Previous conversation:\n{history}\n\n"
        f"Current customer email:\n{message.body}"
    )
    prompt = build_email_prompt(full_input, [context])
    response = LLMClient().generate(prompt)
    confidence = calculate_confidence(chunks, response)

    logger.info(
        "Generated draft for message %s (confidence=%s)", message.id, confidence
    )
    return {"reply": response, "confidence": confidence}
