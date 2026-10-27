"""LangGraph agent — Customer question -> FastAPI -> LangGraph -> LLM -> Tools -> Database.

Graph:
    START -> "llm" -> (has tool_calls? -> "tools" -> "llm" ... : END)
"""
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from tools import tools

SYSTEM_PROMPT = """Bạn là nhân viên tư vấn bán xe AI thân thiện, chuyên nghiệp của showroom ô tô "AutoShop".
Quy tắc:
- Luôn trả lời bằng ngôn ngữ của khách (mặc định tiếng Việt).
- Với MỌI câu hỏi về xe, giá, khuyến mãi, màu, tồn kho, thông số, so sánh, tư vấn chọn xe: BẮT BUỘC gọi tool để lấy dữ liệu mới nhất từ database. KHÔNG được tự bịa giá, khuyến mãi hay tồn kho.
- Khi khách cần tư vấn, hiểu nhu cầu (ngân sách, số chỗ, mục đích: đi phố / gia đình / đường dài / chở hàng, nhiên liệu) rồi tìm xe phù hợp; nếu thiếu thông tin quan trọng, hỏi lại ngắn gọn.
- Nếu không tìm thấy xe, nói rõ và gợi ý mẫu tương tự (gọi tool để tìm).
- Nếu xe hết hàng, thông báo có thể đặt cọc chờ xe và gợi ý mẫu thay thế còn sẵn.
- Giá trong dữ liệu là giá niêm yết, chưa gồm lệ phí trước bạ, biển số, bảo hiểm — nhắc khách khi báo giá.
- Trình bày ngắn gọn, rõ ràng; dùng gạch đầu dòng khi liệt kê; hiển thị giá dạng 545.000.000₫ (hoặc "545 triệu").
- Cuối câu trả lời có thể mời khách đăng ký lái thử hoặc để lại số điện thoại để được tư vấn.
- Với câu hỏi ngoài phạm vi showroom, lịch sự từ chối và hướng khách về các mẫu xe."""


def build_llm():
    import os

    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        temperature=0,
    ).bind_tools(tools)


llm = build_llm()


def call_llm(state: MessagesState):
    """LLM node: understand the customer question, then answer or call a Product Tool."""
    return {"messages": [llm.invoke(state["messages"])]}


def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    return "tools" if getattr(last, "tool_calls", None) else END


# Build the graph: START -> llm -> (tools <-> llm) -> END
builder = StateGraph(MessagesState)
builder.add_node("llm", call_llm)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
builder.add_edge("tools", "llm")
app_graph = builder.compile()


def build_initial_messages(question: str, history: list[dict]) -> list:
    """System prompt + conversation history + new customer question."""
    messages = [SystemMessage(SYSTEM_PROMPT)]
    for item in history[-20:]:
        role, content = item.get("role"), str(item.get("content", ""))
        if role == "assistant":
            messages.append(AIMessage(content))
        else:
            messages.append(HumanMessage(content))
    messages.append(HumanMessage(question))
    return messages