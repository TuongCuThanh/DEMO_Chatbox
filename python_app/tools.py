"""Product Tools — the functions the LangGraph agent can call.
Every call queries SQLite directly, so answers always use the latest data.
"""
from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from db import get_conn, init_db, rows_to_dicts
 
init_db()


# ---------------- Tool 1: search cars ----------------
class SearchCarsArgs(BaseModel):
    keyword: Optional[str] = Field(None, description="Từ khóa trong tên/phiên bản/mô tả, ví dụ 'Vios', 'CX-5', 'hybrid'")
    brand: Optional[str] = Field(None, description="Hãng xe, ví dụ Toyota, Honda, Hyundai, Mazda, Kia, Ford, VinFast")
    body_type: Optional[Literal["Sedan", "SUV", "Hatchback", "MPV", "Bán tải"]] = Field(None, description="Kiểu dáng")
    fuel: Optional[Literal["Xăng", "Dầu", "Hybrid", "Điện"]] = Field(None, description="Loại nhiên liệu")
    min_seats: Optional[int] = Field(None, description="Số chỗ tối thiểu (ví dụ 7 cho gia đình đông người)")
    min_price: Optional[int] = Field(None, description="Giá tối thiểu (VND)")
    max_price: Optional[int] = Field(None, description="Giá tối đa (VND), ví dụ 600000000 cho 'dưới 600 triệu'")
    in_stock_only: Optional[bool] = Field(None, description="Chỉ lấy xe còn sẵn tại showroom")
    has_promotion: Optional[bool] = Field(None, description="Chỉ lấy xe đang có khuyến mãi")
    sort: Optional[Literal["price_asc", "price_desc", "name"]] = Field(None, description="Sắp xếp kết quả")
    limit: Optional[int] = Field(10, description="Số kết quả tối đa (mặc định 10)")


def _format(c: dict) -> dict:
    return {
        "id": c["id"],
        "sku": c["sku"],
        "name": f'{c["brand"]} {c["model"]} {c["version"] or ""}'.strip(),
        "brand": c["brand"],
        "model": c["model"],
        "version": c["version"],
        "year": c["year"],
        "body_type": c["body_type"],
        "fuel": c["fuel"],
        "transmission": c["transmission"],
        "seats": c["seats"],
        "engine": c["engine"],
        "price_vnd": c["price"],
        "price_text": f'{c["price"]:,}₫'.replace(",", "."),
        "promotion": c["promotion"] or "Không có",
        "stock": c["stock"],
        "status": f'Còn {c["stock"]} xe tại showroom' if c["stock"] > 0 else "Hết xe (nhận đặt cọc chờ xe về)",
        "colors": c["colors"],
        "description": c["description"],
        "updated_at": c["updated_at"],
    }


@tool("search_cars", args_schema=SearchCarsArgs)
def search_cars(
    keyword: Optional[str] = None,
    brand: Optional[str] = None,
    body_type: Optional[str] = None,
    fuel: Optional[str] = None,
    min_seats: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    in_stock_only: Optional[bool] = None,
    has_promotion: Optional[bool] = None,
    sort: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """Tìm kiếm xe trong showroom theo hãng, kiểu dáng, nhiên liệu, số chỗ, khoảng giá,
    tình trạng còn xe, khuyến mãi. Dùng cho MỌI câu hỏi về xe, giá, tồn kho, so sánh."""
    where, params = [], []
    if keyword:
        where.append("(brand || ' ' || model || ' ' || IFNULL(version,'') || ' ' || IFNULL(description,'') || ' ' || sku LIKE ?)")
        params.append(f"%{keyword}%")
    if brand:
        where.append("brand LIKE ?")
        params.append(brand)
    if body_type:
        where.append("body_type = ?")
        params.append(body_type)
    if fuel:
        where.append("fuel = ?")
        params.append(fuel)
    if min_seats is not None:
        where.append("seats >= ?")
        params.append(min_seats)
    if min_price is not None:
        where.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("price <= ?")
        params.append(max_price)
    if in_stock_only:
        where.append("stock > 0")
    if has_promotion:
        where.append("promotion IS NOT NULL AND promotion <> ''")

    order_by = {"price_asc": "price ASC", "price_desc": "price DESC", "name": "brand ASC, model ASC"}.get(sort, "id ASC")
    safe_limit = min(max(int(limit or 10), 1), 50)

    sql = "SELECT * FROM cars"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order_by} LIMIT {safe_limit}"

    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(sql, params).fetchall())
    return {"count": len(rows), "cars": [_format(r) for r in rows]}


# ---------------- Tool 2: car details ----------------
class GetCarDetailsArgs(BaseModel):
    id: Optional[int] = Field(None, description="ID xe")
    sku: Optional[str] = Field(None, description="Mã SKU xe")


@tool("get_car_details", args_schema=GetCarDetailsArgs)
def get_car_details(id: Optional[int] = None, sku: Optional[str] = None) -> dict:
    """Lấy thông số chi tiết, giá, khuyến mãi, màu và tồn kho mới nhất của MỘT xe theo id hoặc SKU."""
    if id is not None:
        query, params = "SELECT * FROM cars WHERE id = ?", (id,)
    elif sku:
        query, params = "SELECT * FROM cars WHERE sku = ?", (sku,)
    else:
        return {"error": "Cần cung cấp id hoặc sku"}

    with get_conn() as conn:
        row = conn.execute(query, params).fetchone()
    return _format(dict(row)) if row else {"error": "Không tìm thấy xe"}


# ---------------- Tool 3: showroom overview ----------------
@tool("list_showroom_overview")
def list_showroom_overview() -> dict:
    """Liệt kê các hãng, kiểu dáng, loại nhiên liệu đang có trong showroom kèm số mẫu xe và khoảng giá."""
    with get_conn() as conn:
        return {
            "brands": rows_to_dicts(conn.execute(
                "SELECT brand, COUNT(*) AS models, MIN(price) AS min_price, MAX(price) AS max_price FROM cars GROUP BY brand"
            ).fetchall()),
            "body_types": rows_to_dicts(conn.execute(
                "SELECT body_type, COUNT(*) AS models FROM cars GROUP BY body_type"
            ).fetchall()),
            "fuels": rows_to_dicts(conn.execute(
                "SELECT fuel, COUNT(*) AS models FROM cars GROUP BY fuel"
            ).fetchall()),
        }


tools = [search_cars, get_car_details, list_showroom_overview]