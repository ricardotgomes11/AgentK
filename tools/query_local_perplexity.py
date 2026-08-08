import json
import urllib.request
from langchain_core.tools import tool


@tool
def query_local_perplexity(query: str) -> str:
    """Queries the local Perplexity server or local SLM node for direct core web research."""
    # Attempt 1: Local Perplexity endpoint at port 8080
    try:
        data = json.dumps({"prompt": query}).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/perplexity/ask",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            result = json.loads(res.read().decode("utf-8"))
            if "text" in result:
                return result["text"]
    except Exception:
        pass

    # Attempt 2: Local Ollama node fallback at port 11434
    try:
        data = json.dumps({
            "model": "gemma2:9b",
            "prompt": query,
            "stream": False
        }).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            result = json.loads(res.read().decode("utf-8"))
            return result.get("response", "Error: No text payload.")
    except Exception as ex:
        return f"Execution Fault: {ex}"
