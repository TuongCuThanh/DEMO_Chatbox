"""Chẩn đoán realtime: đổi giá Vios qua API rồi hỏi lại chat (có/không history)."""
import json
import urllib.request

BASE = "http://127.0.0.1:3000"


def req(method, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=180) as resp:
        return json.load(resp)


# 1) Giá hiện tại trong DB
before = req("GET", "/api/cars")[0]
print("1) DB truoc do:", before["brand"], before["model"], before["price"], "stock", before["stock"])

# 2) Đổi giá Vios thành 535.000.000
after = req("PATCH", "/api/cars/1", {"price": 535000000})
print("2) DB sau PATCH:", after["brand"], after["model"], after["price"], "updated_at", after["updated_at"])

# 3) Hỏi lại KHÔNG history (giống F5)
q = "Toyota Vios gia bao nhieu?"
r = req("POST", "/api/chat", {"message": q, "history": []})
print("3) Tools:", [(t["tool"], t["input"]) for t in r["toolCalls"]])
print("   Cau tra loi (khong history):", r["answer"][:700])

# 4) Hỏi lại CÓ history (chat cũ, chưa F5) — có câu trả lời giá cũ trong lịch sử
r2 = req("POST", "/api/chat", {
    "message": "Hoi lai: Toyota Vios gia bao nhieu vay?",
    "history": [{"role": "user", "content": q},
                {"role": "assistant", "content": "Toyota Vios gia 545.000.000 dong"}],
})
print("4) Tools:", [(t["tool"], t["input"]) for t in r2["toolCalls"]])
print("   Cau tra loi (co history gia cu):", r2["answer"][:700])