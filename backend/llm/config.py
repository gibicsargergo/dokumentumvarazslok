import os

# --- LLM Settings ----------------------------------------------------------
# Environment variables set for local llm use
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "no-key-required")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://192.168.0.53:8080/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "local-model")
# Creativity and diversity of words in the result answer.
# At a low value (0.0 - 0.2) the answer will be deterministic and fact based.
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
