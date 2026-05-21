import logging

from sqlalchemy.orm import Session

from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt
from app.rag.rag_pipeline import get_rag_context
from backend.models.email import Email
from backend.models.enums import MessageDirection
from backend.models.message import Message

logger = logging.getLogger(__name__)


# -------- THREAD HISTORY --------
def get_thread_history(db, thread_id):

    emails = db.query(Email).filter(
        Email.thread_id == thread_id
    ).order_by(Email.id.asc()).all()

    history = []

    for e in emails:
        history.append(f"Customer: {e.body}")
        if e.ai_reply:
            history.append(f"Support: {e.ai_reply}")

    return "\n".join(history)


# -------- CONFIDENCE FUNCTION --------
def calculate_confidence(context, response):

    score = 0

    # context strength
    if context and len(context) > 50:
        score += 40

    # response length (basic quality signal)
    if response and len(response) > 100:
        score += 30

    # fallback detection
    if "not enough information" not in response.lower():
        score += 30

    return min(score, 100)


# -------- MAIN FUNCTION --------
def generate_email_reply(email_body, company_id, db=None, thread_id=None):

    # -------- RAG CONTEXT --------
    context = get_rag_context(email_body, company_id)

    # -------- THREAD HISTORY --------
    history = ""
    if db and thread_id:
        history = get_thread_history(db, thread_id)

    # -------- MERGED INPUT --------
    full_input = f"""
Previous conversation:
{history}

Current customer email:
{email_body}
"""

    # -------- PROMPT --------
    prompt = build_email_prompt(full_input, [context])

    # -------- LLM --------
    llm = LLMClient()
    response = llm.generate(prompt)

    # -------- CONFIDENCE --------
    confidence = calculate_confidence(context, response)

    return {
        "reply": response,
        "confidence": confidence
    }


# ========== Message/Ticket-based generation (Phase 2 chunk 3) ==========
# The functions above are the legacy emails-based path, removed when the
# emails table is dropped at the end of chunk 3.


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

