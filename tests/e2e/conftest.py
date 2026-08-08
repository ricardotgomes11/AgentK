import os

# Set mock OpenAI API key for offline deterministic testing environment
os.environ.setdefault("OPENAI_API_KEY", "mock-openai-key-for-e2e-testing")
os.environ.setdefault("DEFAULT_MODEL_TEMPERATURE", "0")
