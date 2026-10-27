"""Database layer — SQLite (stdlib) with car showroom schema + sample data.

Shares showroom.db with the Node version, so both stacks read/write the same data.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "showroom.db"

DDL = """
CREATE TABLE IF NOT EXISTS cars (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  sku          TEXT UNIQUE NOT NULL,
  brand        TEXT NOT NULL,
  model        TEXT NOT NULL,
  version      TEXT,
  year         INTEGER NOT NULL,
  body_type    TEXT NOT NULL,
  fuel         TEXT NOT NULL,
  transmission TEXT NOT NULL,
  seats        INTEGER NOT NULL,
  engine       TEXT,
  price        INTEGER NOT NULL,
  promotion    TEXT,
  stock        INTEGER NOT NULL DEFAULT 0,
  colors       TEXT,
  description  TEXT,
  updated_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""

# Bảng lưu thông tin khách hàng trích xuất từ chat (Extraction Agent)
CUSTOMERS_DDL = """
CREATE TABLE IF NOT EXISTS customers (
  customer_id          TEXT PRIMARY KEY,
  conversation_id      TEXT,
  name                 TEXT DEFAULT '',
  phone                TEXT DEFAULT '',
  product_interest     TEXT DEFAULT '',
  customer_need        TEXT DEFAULT '',
  budget               TEXT DEFAULT '',
  channel              TEXT DEFAULT 'webchat',
  conversation_summary TEXT DEFAULT '',
  status               TEXT DEFAULT 'new',
  last_interaction_at  TEXT,
  updated_at           TEXT
);
"""

INSERT_SQL = """
INSERT INTO cars (sku, brand, model, version, year, body_type, fuel, transmission,
                  seats, engine, price, promotion, stock, colors, description)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

SEED = [
    ("TOY-VIOS-G", "Toyota", "Vios", "1.5G CVT", 2025, "Sedan", "Xăng", "Số tự động", 5, "1.5L, 107 mã lực", 545000000, "Hỗ trợ 50% lệ phí trước bạ", 7, "Trắng, Đen, Bạc, Đỏ", "Sedan hạng B bền bỉ, tiết kiệm nhiên liệu, giữ giá tốt."),
    ("TOY-CROSS-HEV", "Toyota", "Corolla Cross", "1.8 HEV", 2025, "SUV", "Hybrid", "Số tự động", 5, "1.8L Hybrid, 138 mã lực", 905000000, None, 3, "Trắng ngọc trai, Xám, Đen", "SUV hạng C hybrid, tiêu hao ~4.5L/100km, gói an toàn TSS."),
    ("TOY-FORT-LEG", "Toyota", "Fortuner", "2.8 Legender 4x4 AT", 2025, "SUV", "Dầu", "Số tự động", 7, "2.8L Diesel, 201 mã lực", 1350000000, "Tặng bảo hiểm thân vỏ 1 năm", 2, "Trắng, Đen", "SUV 7 chỗ khung gầm rời, dẫn động 4 bánh."),
    ("HON-CITY-RS", "Honda", "City", "RS", 2025, "Sedan", "Xăng", "Số tự động", 5, "1.5L, 119 mã lực", 569000000, "Giảm 20 triệu tiền mặt", 5, "Đỏ, Trắng, Xám", "Sedan hạng B thể thao, Honda Sensing."),
    ("HON-CRV-L", "Honda", "CR-V", "L AWD", 2025, "SUV", "Xăng", "Số tự động", 7, "1.5L Turbo, 188 mã lực", 1259000000, None, 0, "Trắng, Đen, Xanh", "SUV 5+2 chỗ, dẫn động AWD, nội thất rộng rãi."),
    ("HYU-ACC-AT", "Hyundai", "Accent", "1.5 AT Đặc biệt", 2025, "Sedan", "Xăng", "Số tự động", 5, "1.5L, 115 mã lực", 569000000, "Giảm 15 triệu + tặng phụ kiện", 10, "Trắng, Đen, Bạc, Đỏ, Xanh", "Sedan hạng B nhiều tiện nghi, màn hình 10.25 inch."),
    ("HYU-STAR-SE", "Hyundai", "Stargazer X", "1.5 AT Cao cấp", 2025, "MPV", "Xăng", "Số tự động", 7, "1.5L, 115 mã lực", 599000000, None, 4, "Trắng, Bạc, Xám", "MPV 7 chỗ giá tốt cho gia đình."),
    ("MAZ-CX5-PREM", "Mazda", "CX-5", "2.0 Premium", 2025, "SUV", "Xăng", "Số tự động", 5, "2.0L, 154 mã lực", 829000000, "Ưu đãi 30 triệu", 6, "Đỏ pha lê, Trắng, Xám", "SUV hạng C thiết kế KODO, i-Activsense."),
    ("KIA-MORN-AT", "Kia", "Morning", "1.25 AT Premium", 2025, "Hatchback", "Xăng", "Số tự động", 5, "1.25L, 83 mã lực", 424000000, None, 8, "Trắng, Đỏ, Vàng", "Xe đô thị cỡ nhỏ, dễ lái, tiết kiệm."),
    ("FORD-RNG-WT", "Ford", "Ranger", "Wildtrak 2.0 Bi-Turbo 4x4", 2025, "Bán tải", "Dầu", "Số tự động", 5, "2.0L Bi-Turbo Diesel, 210 mã lực", 979000000, "Tặng nắp thùng", 3, "Cam, Trắng, Đen", "Bán tải bán chạy nhất, 4x4, SYNC 4A."),
    ("VF-VF5-PLUS", "VinFast", "VF 5", "Plus", 2025, "Hatchback", "Điện", "Số tự động", 5, "Điện 134 mã lực, ~326 km/lần sạc", 529000000, "Miễn phí sạc đến 2027", 15, "Vàng, Trắng, Xanh", "Hatchback điện cỡ A, chi phí vận hành thấp."),
    ("VF-VF8-PLUS", "VinFast", "VF 8", "Plus", 2025, "SUV", "Điện", "Số tự động", 5, "Điện 402 mã lực, ~457 km/lần sạc", 1199000000, "Miễn phí sạc đến 2027", 0, "Xanh, Trắng, Đen", "SUV điện hạng D, dẫn động AWD."),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(DDL)
        conn.executescript(CUSTOMERS_DDL)
        count = conn.execute("SELECT COUNT(*) AS c FROM cars").fetchone()["c"]
        if count == 0:
            conn.executemany(INSERT_SQL, SEED)
            print(f"[db] Seeded {len(SEED)} cars into {DB_PATH}")


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


if __name__ == "__main__":
    import sys

    if "--reset" in sys.argv:
        # Xóa bảng cũ để seed lại theo nội dung mới trong db.py.
        # Lưu ý: mọi giá trị đã sửa qua admin/API/DB Browser sẽ bị mất.
        with get_conn() as conn:
            conn.execute("DROP TABLE IF EXISTS cars")
        print("[db] Dropped table 'cars'")

    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT price, stock FROM cars WHERE id = 1").fetchone()
    