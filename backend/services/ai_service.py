"""AI draft generation for inbound Messages — RAG retrieval + LLM + a
confidence heuristic. Persistence is handled by ticket_service.
"""

import logging

from sqlalchemy.orm import Session

from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt
from app.rag.rag_pipeline import get_rag_context
from backend.models.enums import MessageDirection
from backend.models.message import Message

logger = logging.getLogger(__name__)


def calculate_confidence(context: str, response: str) -> int:
    """Heuristic 0-100 confidence. Retrieval-grounded scoring is Phase 4."""
    score = 0
    if context and len(context) > 50:
        score += 40
    if response and len(response) > 100:
        score += 30
    if "not enough information" not in response.lower():
        score += 30
    return min(score, 100)


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
    context = get_rag_context(message.body, message.company_id)
    history = get_ticket_history(
        db, message.ticket_id, before_message_id=message.id
    )

    full_input = (
        f"Previous conversation:\n{history}\n\n"
        f"Current customer email:\n{message.body}"
    )
    prompt = build_email_prompt(full_input, [context])
    response = LLMClient().generate(prompt)
    confidence = calculate_confidence(context, response)

    logger.info(
        "Generated draft for message %s (confidence=%s)", message.id, confidence
    )
    return {"reply": response, "confidence": confidence}
