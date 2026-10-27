"""Test end-to-end: chat có thông tin khách -> Extraction Agent -> Google Sheet."""
import json
import time
import urllib.request

payload = {
    "message": "Chao ban, toi ten Tran Thi B, so DT 0987654321. Toi dang tim mua xe gia dinh 7 cho duoi 700 trieu.",
    "history": [],
    "customer_id": "TEST-LEAD-001",
    "conversation_id": "T-TEST-001",
}
req = urllib.request.Request(
    "http://127.0.0.1:3000/api/chat",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=180) as resp:
    data = json.load(resp)

print("tools:", [(t["tool"], t["input"]) for t in data["toolCalls"]])
print("answer:", data["answer"][:500])
print("cho background task (Extraction Agent) hoan thanh...")
time.sleep(15)
print("xong - xem log server de xem dong [extract]")