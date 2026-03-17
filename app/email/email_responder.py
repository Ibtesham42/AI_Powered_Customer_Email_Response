from app.rag.rag_pipeline import RAGPipeline
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt


class EmailResponder:

    def __init__(self):

        self.rag = RAGPipeline()

        self.llm = LLMClient()


    def generate_reply(self, customer_email):

        retrieved_context = self.rag.retrieve(customer_email)

        prompt = build_email_prompt(customer_email, retrieved_context)

        response = self.llm.generate(prompt)

        return response