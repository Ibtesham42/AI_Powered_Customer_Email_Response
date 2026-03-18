from groq import Groq
from app.utils.config import Config


class LLMClient:

    def __init__(self):

        self.client = Groq(api_key=Config.GROQ_API_KEY)

        self.model = "llama-3.3-70b-versatile"

        print("LLM connected:", self.model)


    def generate(self, prompt):

        stream = self.client.chat.completions.create(

            model=self.model,

            messages=[
                {"role": "system", "content": "You are a professional customer support assistant."},
                {"role": "user", "content": prompt}
            ],

            temperature=0.3,
            max_tokens=500,

            stream=True
        )

        full_response = ""

        for chunk in stream:

            if chunk.choices[0].delta.content:

                token = chunk.choices[0].delta.content

                print(token, end="", flush=True)

                full_response += token

        print("\n")

        return full_response