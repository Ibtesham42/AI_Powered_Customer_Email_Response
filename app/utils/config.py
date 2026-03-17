from dotenv import load_dotenv
import os

load_dotenv()

class Config:

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
    MODEL_NAME = os.getenv("MODEL_NAME", "llama3-70b-8192")