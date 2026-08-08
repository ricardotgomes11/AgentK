import os
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

default_model_temperature = int(os.getenv("DEFAULT_MODEL_TEMPERATURE", "0"))
default_model_provider = os.getenv("DEFAULT_MODEL_PROVIDER", "OPENAI").upper()
default_model_name = os.getenv("DEFAULT_MODEL_NAME", "gpt-4o")

ollama_base_url = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/v1")

match default_model_provider:
    case "OPENAI":
        api_key = os.getenv("OPENAI_API_KEY", "mock_key")
        default_langchain_model = ChatOpenAI(model_name=default_model_name, temperature=default_model_temperature, api_key=api_key)
    case "ANTHROPIC":
        api_key = os.getenv("ANTHROPIC_API_KEY", "mock_key")
        default_langchain_model = ChatAnthropic(model_name=default_model_name, temperature=default_model_temperature, api_key=api_key)
    case "OLLAMA" | "LOCAL":
        ollama_model = os.getenv("DEFAULT_MODEL_NAME", "gemma2:9b")
        default_langchain_model = ChatOpenAI(
            model_name=ollama_model,
            temperature=default_model_temperature,
            api_key="ollama",
            base_url=ollama_base_url,
        )
    case _:
        raise ValueError(f"Unsupported model provider: {default_model_provider}")

