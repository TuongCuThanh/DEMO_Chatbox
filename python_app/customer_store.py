"""Lưu lead khách hàng vào SQLite (thay cho Google Sheet).

Cùng schema HEADERS như bản Google Sheet để dễ chuyển đổi sau này.
"""
from db import get_conn, rows_to_dicts

HEADERS = [
    "customer_id",
    "conversation_id",
    "name",
    "phone",
    "product_interest",
    "customer_need",
    "budget",
    "channel",
    "conversation_summary",
    "status",
    "last_interaction_at",
    "updated_at",
]


def upsert_customer(data: dict) -> None:
    """Tạo hồ sơ mới nếu chưa có customer_id; nếu đã có thì cập nhật các trường
    KHÔNG được ghi đè bằng chuỗi rỗng (giống ngữ nghĩa upsert trên Google Sheet)."""
    customer_id = data.get("customer_id")
    if not customer_id:
        raise ValueError("customer_id is required")

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()

        if existing:
            merged = dict(existing)
            for key, value in data.items():
                if key in HEADERS and value not in (None, ""):
                    merged[key] = value
            conn.execute(
                """UPDATE customers SET conversation_id = ?, name = ?, phone = ?,
                   product_interest = ?, customer_need = ?, budget = ?, channel = ?,
                   conversation_summary = ?, status = ?, last_interaction_at = ?,
                   updated_at = ? WHERE customer_id = ?""",
                (
                    merged["conversation_id"], merged["name"], merged["phone"],
                    merged["product_interest"], merged["customer_need"], merged["budget"],
                    merged["channel"], merged["conversation_summary"], merged["status"],
                    merged["last_interaction_at"], merged["updated_at"], customer_id,
                ),
            )
        else:
            row = {h: data.get(h) or "" for h in HEADERS}
            conn.execute(
                """INSERT INTO customers (customer_id, conversation_id, name, phone,
                   product_interest, customer_need, budget, channel,
                   conversation_summary, status, last_interaction_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(row[h] for h in HEADERS),
            )


def list_customers() -> list[dict]:
    """Đọc toàn bộ hồ sơ khách theo thứ tự THÊM MỚI (dòng cũ giữ nguyên vị trí)."""
    with get_conn() as conn:
        return rows_to_dicts(
            conn.execute("SELECT * FROM customers ORDER BY rowid ASC").fetchall()
        )