import re
import logging

from app.rag.rag_pipeline import RAGPipeline
from app.llm.llm_client import LLMClient
from app.llm.prompt_builder import build_email_prompt


class EmailResponder:

    def __init__(self, user_id):

        self.user_id = user_id
        self.rag = RAGPipeline(user_id)
        self.llm = LLMClient()

        logging.info(f"EmailResponder initialized for user: {user_id}")

    
    # Clean LLM Output
    

    def clean_response(self, response):

        if "Subject:" in response:
            response = response[response.index("Subject:"):]

        return response.strip()

    
    # Extraction Utilities
    

    def extract_order_id(self, text):

        match = re.search(r"\b\d{5,}\b", text)

        return match.group() if match else None


    def extract_email(self, text):

        match = re.search(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )

        return match.group() if match else None


    def extract_ticket_id(self, text):

        match = re.search(r"\bT\d+\b", text, re.IGNORECASE)

        return match.group() if match else None


    def extract_project_name(self, text):

        # project "Name"
        match = re.search(
            r'project\s+"([^"]+)"',
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

        # fallback: words before "project"
        match = re.search(
            r'([A-Za-z\s]+)\s+project',
            text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return None



    # Search Helper
    

    def search_documents(self, keyword):

        results = []

        keyword = keyword.lower()

        for doc in self.rag.documents:

            if keyword in doc["text"].lower():

                results.append(doc["text"])

                if len(results) >= 3:
                    break

        return results


    
    # MAIN PIPELINE
    

    def generate_reply(self, customer_email):

        logging.info("Processing new customer email")

        order_id = self.extract_order_id(customer_email)
        email_id = self.extract_email(customer_email)
        ticket_id = self.extract_ticket_id(customer_email)
        project_name = self.extract_project_name(customer_email)

        retrieved_context = []

        
        #  Project search
        

        if project_name:

            logging.info(f"Searching project: {project_name}")

            retrieved_context = self.search_documents(project_name)


        
        # Order search
        

        if not retrieved_context and order_id:

            logging.info(f"Searching order: {order_id}")

            retrieved_context = self.search_documents(order_id)


        
        # Ticket search
        

        if not retrieved_context and ticket_id:

            logging.info(f"Searching ticket: {ticket_id}")

            retrieved_context = self.search_documents(ticket_id)


        
        #  Email searching
        

        if not retrieved_context and email_id:

            logging.info(f"Searching email: {email_id}")

            retrieved_context = self.search_documents(email_id)


        
        # Vector search fallback
        

        if not retrieved_context:

            logging.info("Using vector search fallback")

            retrieved_context = self.rag.retrieve(customer_email)


        print("\nRetrieved Context:")
        print(retrieved_context)


        
        # Buildd Prompt
        

        prompt = build_email_prompt(
            customer_email,
            retrieved_context
        )


        # -------------------------------------
        # Generate LLM response
        # -------------------------------------

        response = self.llm.generate(prompt)

        response = self.clean_response(response)

        return response