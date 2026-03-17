from groq import Groq
from app.utils.config import Config


class LLMClient:

    def __init__(self):

        self.client = Groq(api_key=Config.GROQ_API_KEY)

        self.model = "llama-3.3-70b-versatile"

        print("LLM connected:", self.model)


    def generate(self, prompt):

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[
                {"role": "user", "content": prompt}
            ],

            temperature=0.2,
            max_tokens=500
        )

        return response.choices[0].message.content