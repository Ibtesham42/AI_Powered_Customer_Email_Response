from app.rag.rag_pipeline import get_rag_context
from app.llm.prompt_builder import build_email_prompt
from app.llm.llm_client import LLMClient


def generate_email_reply(email_body, company_id):

    #  get context from RAG
    context = get_rag_context(email_body, company_id)

    #  build prompt (YOU ALREADY HAVE THIS)
    prompt = build_email_prompt(email_body, [context])

    #  call LLM
    llm = LLMClient()
    response = llm.generate(prompt)

    return response