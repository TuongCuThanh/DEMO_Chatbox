"""Dọn dòng test + kiểm tra thứ tự customers."""
from customer_store import list_customers
from db import get_conn

with get_conn() as conn:
    deleted = conn.execute(
        "DELETE FROM customers WHERE customer_id IN ('TEST-XE-3','TEST-XE-4')"
    ).rowcount
print("da xoa", deleted, "dong test")

rows = list_customers()
print("tong so:", len(rows))
for i, r in enumerate(rows, start=1):
    print(i, r["customer_id"], repr(r["name"]), r["phone"])