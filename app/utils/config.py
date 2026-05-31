import os

from dotenv import load_dotenv

load_dotenv()


class Config:

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
    # Active Groq model + generation params. These were hardcoded in
    # app/llm/llm_client.py; LLMClient now reads them from here so the model
    # and tuning live in one place (env-overridable).
    MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
    LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))

    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")
