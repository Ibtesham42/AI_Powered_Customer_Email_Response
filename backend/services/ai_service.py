"""AI draft generation for inbound Messages.

A single structured Groq call returns ``{intent, confidence, needs_human,
draft}``; this module parses and validates it (with a safe defer-to-human
fallback) and blends the model's self-rating with retrieval similarity into the
final confidence. Persistence is handled by ``ticket_service.record_ai_draft``.
"""

import json
import logging

from sqlalchemy.orm import Session

from app.llm.llm_client import get_llm_client
from app.llm.prompt_builder import build_structured_prompt, build_summary_prompt
from backend.models.enums import Intent, MessageDirection
from backend.models.kb_chunk import KbChunk
from backend.models.message import Message
from backend.models.ticket import Ticket
from backend.services import rag_service, ticket_service

logger = logging.getLogger(__name__)

# Past-Ticket summaries injected as memory are capped to this many characters so
# a Customer with a long history can't blow the prompt's token budget.
PAST_SUMMARY_CHAR_BUDGET = 1500

# Phrases that signal the model could not answer from context — a reply built
# on one of these must not score as confident, however good the retrieval was.
_FALLBACK_PHRASES = (
    "not enough information",
    "could not find",
    "couldn't find",
    "do not have",
    "don't have",
    "unable to find",
    "no information",
)


def calculate_confidence(
    chunks: list[tuple[KbChunk, float]],
    draft: str,
    llm_confidence: int,
) -> int:
    """Final confidence 0-100: retrieval similarity (primary) blended with the
    model's self-rating (secondary), then damped on explicit non-answers.

    Retrieval is the dominant signal — a reply the KB cannot support must not
    score high no matter how sure the model claims to be. With nothing
    retrieved, we cap hard and lean on the (already low) self-rating.
    """
    llm_confidence = max(0, min(100, llm_confidence))

    if not chunks:
        score = float(min(llm_confidence, 15))  # KB had nothing to support it
    else:
        # pgvector cosine_distance is in [0, 2]; similarity = 1 - distance.
        top_distance = chunks[0][1]
        similarity = max(0.0, min(1.0, 1.0 - top_distance))
        retrieval_score = similarity * 100.0
        score = 0.7 * retrieval_score + 0.3 * llm_confidence

    if draft and any(phrase in draft.lower() for phrase in _FALLBACK_PHRASES):
        score *= 0.5

    return int(max(0.0, min(score, 100.0)))


def _validate_intent(value: object) -> str:
    """Coerce the model's intent to a known value, defaulting to general."""
    try:
        return Intent(str(value)).value
    except (ValueError, TypeError):
        return Intent.GENERAL_SUPPORT.value


def _coerce_confidence(value: object) -> int:
    """Coerce the model's self-rating to an int in [0, 100]."""
    try:
        return max(0, min(100, int(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def get_ticket_history(
    db: Session, ticket_id: int, before_message_id: int | None = None
) -> str:
    """Prior Messages on a Ticket, formatted as conversation history."""
    query = db.query(Message).filter(Message.ticket_id == ticket_id)
    if before_message_id is not None:
        query = query.filter(Message.id < before_message_id)

    lines = []
    for m in query.order_by(Message.id.asc()).all():
        speaker = "Customer" if m.direction == MessageDirection.INBOUND else "Support"
        lines.append(f"{speaker}: {m.body}")
    return "\n".join(lines)


def _past_ticket_memory(
    db: Session, company_id: int, customer_id: int, exclude_ticket_id: int
) -> str:
    """Bulleted past-Ticket summaries for this Customer, within the char budget."""
    summaries = ticket_service.list_resolved_ticket_summaries(
        db, company_id, customer_id, exclude_ticket_id
    )
    lines: list[str] = []
    used = 0
    for summary in summaries:
        line = f"- {summary.strip()}"
        if used + len(line) + 1 > PAST_SUMMARY_CHAR_BUDGET:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def build_memory(db: Session, message: Message) -> str:
    """The model's working memory for an inbound Message: this Customer's
    past-Ticket summaries (budgeted) + this Ticket's conversation so far + the
    current email. Sections with no content are omitted.
    """
    ticket = ticket_service.get_ticket(db, message.company_id, message.ticket_id)
    history = get_ticket_history(db, message.ticket_id, before_message_id=message.id)

    sections: list[str] = []
    if ticket is not None:
        past = _past_ticket_memory(
            db, message.company_id, ticket.customer_id, ticket.id
        )
        if past:
            sections.append("Past tickets from this customer (summaries):\n" + past)
    if history:
        sections.append("Earlier in this conversation:\n" + history)
    sections.append("Current customer email:\n" + (message.body or ""))
    return "\n\n".join(sections)


def summarize_ticket(db: Session, ticket: Ticket) -> str:
    """One-line internal summary of a Ticket's full conversation, for Memory on
    the Customer's future Tickets. Returns "" when there is nothing to summarise.
    """
    conversation = get_ticket_history(db, ticket.id)
    if not conversation.strip():
        return ""
    summary = get_llm_client().generate(build_summary_prompt(conversation))
    return summary.strip()


def generate_draft(db: Session, message: Message) -> dict:
    """Generate an AI draft reply for an inbound Message.

    Returns ``{"reply": str, "confidence": int, "intent": str,
    "needs_human": bool}``. On a malformed model response we fall back to a
    safe defer-to-human result rather than guessing. Persistence is the
    caller's job — see ``ticket_service.record_ai_draft``.
    """
    chunks = rag_service.retrieve(db, message.body, message.company_id)
    context = "\n".join(chunk.content for chunk, _distance in chunks)
    full_input = build_memory(db, message)
    allowed_intents = [i.value for i in Intent]
    prompt = build_structured_prompt(full_input, [context], allowed_intents)
    raw = get_llm_client().generate_structured(prompt)

    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning(
            "Structured LLM output unparseable for message %s; deferring to human",
            message.id,
        )
        return {
            "reply": "",
            "confidence": 0,
            "intent": Intent.GENERAL_SUPPORT.value,
            "needs_human": True,
        }

    draft = str(data.get("draft") or "").strip()
    intent = _validate_intent(data.get("intent"))
    llm_confidence = _coerce_confidence(data.get("confidence"))
    needs_human = bool(data.get("needs_human", False))

    if draft:
        confidence = calculate_confidence(chunks, draft, llm_confidence)
    else:
        # No usable reply — confidence is in the draft, and there is none. Zero
        # confidence also sorts it to the top of the review queue. A human must
        # take it regardless of the model's flag.
        confidence = 0
        needs_human = True

    logger.info(
        "Generated draft for message %s (intent=%s, confidence=%s, needs_human=%s)",
        message.id,
        intent,
        confidence,
        needs_human,
    )
    return {
        "reply": draft,
        "confidence": confidence,
        "intent": intent,
        "needs_human": needs_human,
    }
