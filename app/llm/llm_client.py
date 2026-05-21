import logging

from groq import Groq

from app.utils.config import Config

logger = logging.getLogger(__name__)


class LLMClient:

    def __init__(self):

        self.client = Groq(api_key=Config.GROQ_API_KEY)

        self.model = "llama-3.3-70b-versatile"

        logger.info("LLM client ready (model=%s)", self.model)


    def generate(self, prompt):

        stream = self.client.chat.completions.create(

            model=self.model,

            messages=[
                {"role": "system", "content": "You are a professional customer support assistant."},
                {"role": "user", "content": prompt}
            ],

            temperature=0.4,
            max_tokens=500,

            stream=True
        )

        full_response = ""

        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content

        logger.debug("LLM generation complete (%d chars)", len(full_response))

        return full_response