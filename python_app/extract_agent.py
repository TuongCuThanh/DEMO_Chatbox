"""Extraction Agent — agent thứ 2 trong workflow:

    lịch sử chat -> [trích xuất thông tin khách] -> Google Sheet (Customers)

Sau mỗi lượt trả lời, agent này đọc toàn bộ hội thoại và trích ra:
tên, số điện thoại, xe quan tâm, nhu cầu, ngân sách, tóm tắt hội thoại,
rồi gọi google_sheets.upsert_customer() để lưu/cập nhật theo customer_id.
"""
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field

load_dotenv()

from customer_store import HEADERS, upsert_customer  # noqa: E402  (SQLite)


class CustomerInfo(BaseModel):
    """Thông tin khách hàng trích xuất từ hội thoại chat."""

    name: str = Field("", description="Họ tên khách hàng. Để '' nếu khách chưa nói.")
    phone: str = Field(
        "",
        description="Số điện thoại của khách (10-11 chữ số, bắt đầu bằng 0). "
        "Chỉ lấy khi khách ĐÃ cung cấp trong hội thoại. Để '' nếu không có.",
    )
    product_interest: str = Field(
        "",
        description="Mẫu xe khách quan tâm, ví dụ 'Toyota Vios', 'SUV 7 chỗ dưới 1 tỷ'. '' nếu chưa rõ.",
    )
    customer_need: str = Field(
        "",
        description="Nhu cầu của khách: mục đích sử dụng, số chỗ, loại nhiên liệu... '' nếu chưa rõ.",
    )
    budget: str = Field(
        "",
        description="Ngân sách khách đưa ra, ví dụ 'dưới 600 triệu', '600000000'. '' nếu chưa nói.",
    )
    conversation_summary: str = Field(
        "",
        description="Tóm tắt hội thoại bằng tiếng Việt trong 1-2 câu (khách quan tâm gì, đã tư vấn gì).",
    )


EXTRACT_SYSTEM_PROMPT = """Bạn là agent trích xuất dữ liệu khách hàng từ lịch sử chat giữa KHÁCH và tư vấn viên AI của showroom ô tô.

Nhiệm vụ: đọc hội thoại và trích xuất thông tin khách hàng theo schema được cho.

Bắt buộc:
- CHỈ trích những thông tin KHÁCH ĐÃ NÓI trong hội thoại. TUYỆT ĐỐI KHÔNG bịa, không suy đoán tên/số điện thoại.
- Số điện thoại: chỉ điền khi khách cung cấp (10-11 chữ số, thường bắt đầu bằng 0), giữ nguyên dạng chữ số.
- conversation_summary: tóm tắt khách quan tâm xe nào, nhu cầu/ngân sách ra sao, tư vấn viên đã gợi ý gì.
- Nếu trường nào không có thông tin, trả về chuỗi rỗng "".
- Ngôn ngữ tiếng Việt."""


def build_extractor():
    import os as _os

    return ChatAnthropic(
        model=_os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=700,
        temperature=0,
    ).with_structured_output(CustomerInfo)


_extractor = build_extractor()


def extract_customer_info(conversation: list[dict]) -> CustomerInfo:
    """Đọc lịch sử chat [{'role','content'}] -> CustomerInfo (dạng Pydantic)."""
    messages = [SystemMessage(EXTRACT_SYSTEM_PROMPT)]
    for item in conversation:
        role, content = item.get("role"), str(item.get("content", ""))
        if not content.strip():
            continue
        messages.append(AIMessage(content) if role == "assistant" else HumanMessage(content))
    # API mới không cho phép hội thoại kết thúc bằng tin nhắn của assistant -> thêm lệnh cuối
    messages.append(HumanMessage("Hãy trích xuất thông tin khách hàng theo schema."))
    return _extractor.invoke(messages)


def has_meaningful_info(info: CustomerInfo) -> bool:
    """Chỉ lưu lên Sheet khi có ít nhất 1 thông tin hành động được (tên/SDT/xe/ngân sách/nhu cầu)."""
    return any([info.name.strip(), info.phone.strip(), info.product_interest.strip(),
                info.budget.strip(), info.customer_need.strip()])


def save_customer_to_sheet(
    customer_id: str,
    conversation_id: str,
    info: CustomerInfo,
    channel: str = "webchat",
) -> dict | None:
    """Gọi google_sheets.upsert_customer để tạo/cập nhật hồ sơ khách."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {h: "" for h in HEADERS}
    row.update(
        customer_id=customer_id,
        conversation_id=conversation_id,
        name=info.name.strip(),
        phone=info.phone.strip(),
        product_interest=info.product_interest.strip(),
        customer_need=info.customer_need.strip(),
        budget=info.budget.strip(),
        channel=channel,
        conversation_summary=info.conversation_summary.strip(),
        status="new",
        last_interaction_at=now,
        updated_at=now,
    )
    upsert_customer(row)
    return row


def process_conversation(customer_id: str, conversation_id: str, conversation: list[dict]) -> dict | None:
    """Entry point chạy nền sau mỗi lượt chat: trích xuất -> lưu Sheet (nếu có dữ liệu)."""
    if not customer_id:
        return None
    info = extract_customer_info(conversation)
    if not has_meaningful_info(info):
        print(f"[extract] khong co thong tin hanh dong duoc, bo qua (customer_id={customer_id})")
        return None
    row = save_customer_to_sheet(customer_id, conversation_id, info)
    print(f"[extract] da luu vao SQLite customers: customer_id={customer_id} "
          f"name={row['name']!r} phone={row['phone']!r} xe={row['product_interest']!r}")
    return row