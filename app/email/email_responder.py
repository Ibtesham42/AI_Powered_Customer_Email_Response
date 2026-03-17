from app.rag.rag_pipeline import RAGPipeline
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt


class EmailResponder:

    def __init__(self, user_id):

        self.user_id = user_id
        self.rag = RAGPipeline(user_id)
        self.llm = LLMClient()


    def clean_response(self, response):

        # Remove prompt duplication
        if "Subject:" in response:
            response = response[response.index("Subject:"):]

        return response.strip()


    def generate_reply(self, customer_email):

        retrieved_context = self.rag.retrieve(customer_email)

        prompt = build_email_prompt(customer_email, retrieved_context)

        response = self.llm.generate(prompt)

        response = self.clean_response(response)

        return response