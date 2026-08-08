import sys
import json
import urllib.request


def materialize():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")

            if method == "initialize":
                response_payload = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "core-perplexity-bridge", "version": "1.0.0"}
                }
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                response_payload = {
                    "tools": [{
                        "name": "query_local_perplexity",
                        "description": "Direct core web query via local SL server.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "The exact parameter."}
                            },
                            "required": ["query"]
                        }
                    }]
                }
            elif method == "tools/call":
                prompt = req.get("params", {}).get("arguments", {}).get("query", "")
                try:
                    data = json.dumps({"prompt": prompt}).encode("utf-8")
                    http_req = urllib.request.Request(
                        "http://localhost:8080/api/perplexity/ask",
                        data=data,
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(http_req, timeout=30) as res:
                        result_data = json.loads(res.read().decode("utf-8"))
                        output = result_data.get("text", "Error: No text payload.")
                except Exception as ex:
                    output = f"Execution Fault: {ex}"

                response_payload = {
                    "content": [{"type": "text", "text": output}]
                }
            else:
                response_payload = {"error": f"Unknown method: {method}"}

            if req_id is not None:
                msg = {"jsonrpc": "2.0", "id": req_id, "result": response_payload}
                sys.stdout.write(json.dumps(msg) + "\n")
                sys.stdout.flush()

        except Exception as e:
            err_msg = {"jsonrpc": "2.0", "id": None, "error": str(e)}
            sys.stdout.write(json.dumps(err_msg) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    materialize()
