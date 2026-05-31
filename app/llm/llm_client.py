import logging

from groq import Groq

from app.utils.config import Config

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper over the Groq chat API.

    Model name and generation params (temperature, max_tokens, timeout) come
    from ``app.utils.config.Config`` — not hardcoded here — so tuning lives in
    one env-overridable place. Construct once per process via
    ``get_llm_client()``; building the Groq client per request is a defect.
    """

    def __init__(self):
        self.model = Config.MODEL_NAME
        self.temperature = Config.LLM_TEMPERATURE
        self.max_tokens = Config.LLM_MAX_TOKENS
        self.client = Groq(api_key=Config.GROQ_API_KEY, timeout=Config.LLM_TIMEOUT)
        logger.info(
            "LLM client ready (model=%s, temperature=%s, max_tokens=%s, timeout=%ss)",
            self.model,
            self.temperature,
            self.max_tokens,
            Config.LLM_TIMEOUT,
        )

    def generate(self, prompt):

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional customer support assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        full_response = ""

        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content

        logger.debug("LLM generation complete (%d chars)", len(full_response))

        return full_response


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return the process-wide LLMClient, constructing it on first use.

    The Groq client (and its connection pool) is built once per process; the
    backend hot path must call this rather than ``LLMClient()`` per email.
    """
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
