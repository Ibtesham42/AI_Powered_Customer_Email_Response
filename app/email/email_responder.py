import re

from app.rag.rag_pipeline import RAGPipeline
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt


class EmailResponder:

    def __init__(self, user_id):

        self.user_id = user_id
        self.rag = RAGPipeline(user_id)
        self.llm = LLMClient()

    def clean_response(self, response):

        if "Subject:" in response:
            response = response[response.index("Subject:"):]

        return response.strip()

    def extract_order_id(self, text):

        match = re.search(r"\b\d{5,}\b", text)

        if match:
            return match.group()

        return None

    def extract_email(self, text):

        match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text
        )

        if match:
            return match.group()

        return None

    def generate_reply(self, customer_email):

        order_id = self.extract_order_id(customer_email)
        customer_email_id = self.extract_email(customer_email)

        retrieved_context = []

        # 1️⃣ Direct order search
        if order_id:

            for doc in self.rag.documents:

                if order_id in doc["text"]:

                    retrieved_context = [doc["text"]]
                    break

        # 2️⃣ Email search
        if not retrieved_context and customer_email_id:

            for doc in self.rag.documents:

                if customer_email_id in doc["text"]:

                    retrieved_context = [doc["text"]]
                    break

        # 3️⃣ fallback vector search
        if not retrieved_context:

            retrieved_context = self.rag.retrieve(customer_email)

        print("Retrieved Context:", retrieved_context)

        prompt = build_email_prompt(customer_email, retrieved_context)

        response = self.llm.generate(prompt)

        response = self.clean_response(response)

        return response