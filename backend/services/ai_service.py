
from app.rag.rag_pipeline import get_rag_context
from app.llm.prompt_builder import build_email_prompt
from app.llm.llm_client import LLMClient
from backend.models.email import Email


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

