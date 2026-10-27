"""End-to-end test: Customer -> FastAPI -> LangGraph -> LLM -> Tools -> Database."""
import json
import urllib.request


def chat(message, history=None):
    payload = json.dumps({"message": message, "history": history or []}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:3000/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)


q1 = "Toyota Vios gia bao nhieu? Con xe khong?"
r1 = chat(q1)
print("Q1:", q1)
print("Q1 tools:", [(t["tool"], t["input"]) for t in r1["toolCalls"]])
print("A1:", r1["answer"])
print("-" * 60)

q2 = "To nha can SUV 7 cho duoi 1 ty, chua co bao nhieu khuyen mai?"
r2 = chat(q2, history=[{"role": "user", "content": q1}, {"role": "assistant", "content": r1["answer"]}])
print("Q2:", q2)
print("Q2 tools:", [(t["tool"], t["input"]) for t in r2["toolCalls"]])
print("A2:", r2["answer"])