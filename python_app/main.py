"""FastAPI server — Customer -> FastAPI -> LangGraph -> LLM -> Tools -> Database.

Run:  python -m uvicorn main:app --port 3000   (from the python_app directory)
"""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field

# Load .env from project root (ANTHROPIC_API_KEY, PORT, GOOGLE_* ...)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db import get_conn, init_db, rows_to_dicts  # noqa: E402
from extract_agent import process_conversation  # noqa: E402
from graph import app_graph, build_initial_messages  # noqa: E402

init_db()

app = FastAPI(title="AutoShop Customer AI Chatbox")


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = Field(default_factory=list)
    customer_id: str = Field("", description="Mã khách trên trình duyệt (localStorage), dùng để upsert Sheet")
    conversation_id: str = Field("", description="Mã phiên hội thoại")


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    # content can be a list of blocks, e.g. [{"type": "text", "text": "..."}]
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return str(content)


@app.post("/api/chat")
def chat(req: ChatRequest, background_tasks: BackgroundTasks) -> dict:
    """Customer question -> LangGraph -> LLM <-> Tools -> Database -> answer.

    Sau khi trả lời, Extraction Agent chạy nền: trích xuất thông tin khách
    từ lịch sử chat và lưu/cập nhật lên Google Sheet (không làm chậm response).
    """
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    history = [m.model_dump() for m in req.history]
    try:
        state = app_graph.invoke({"messages": build_initial_messages(req.message, history)})
    except Exception as exc:  # surface config/API errors to the chat UI
        raise HTTPException(status_code=500, detail=str(exc))

    answer = ""
    tool_calls = []
    for msg in state["messages"]:
        if isinstance(msg, AIMessage):
            for tc in getattr(msg, "tool_calls", None) or []:
                tool_calls.append({"tool": tc.get("name"), "input": tc.get("args")})
            if not getattr(msg, "tool_calls", None):
                text = _message_text(msg.content).strip()
                if text:
                    answer = text
    answer = answer or "Xin lỗi, tôi chưa xử lý được yêu cầu này."

    # Extraction Agent (nền): hội thoại đầy đủ = history + câu hỏi mới + câu trả lời
    conversation = [m.model_dump() for m in req.history] + [
        {"role": "user", "content": req.message},
        {"role": "assistant", "content": answer},
    ]
    background_tasks.add_task(
        _save_lead_safely, req.customer_id, req.conversation_id, conversation
    )
    return {"answer": answer, "toolCalls": tool_calls}


def _save_lead_safely(customer_id: str, conversation_id: str, conversation: list[dict]) -> None:
    """Chạy nền: lỗi Google Sheet không được làm hỏng luồng chat."""
    try:
        process_conversation(customer_id, conversation_id or customer_id, conversation)
    except Exception as exc:  # noqa: BLE001
        print(f"[extract] loi luu Google Sheet: {exc!r}")


# ---------------- Admin: prove the bot reads the latest data ----------------
class CarUpdate(BaseModel):
    price: int | None = None
    stock: int | None = None
    promotion: str | None = None


@app.get("/api/cars")
def list_cars() -> list[dict]:
    with get_conn() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM cars ORDER BY id").fetchall())


@app.get("/api/customers")
def list_customers_endpoint() -> list[dict]:
    """Xem các lead khách hàng đã trích xuất từ chat (lưu trong SQLite)."""
    from customer_store import list_customers

    return list_customers()


@app.patch("/api/cars/{car_id}")
def update_car(car_id: int, body: CarUpdate) -> dict:
    with get_conn() as conn:
        current = conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="Not found")
        conn.execute(
            """UPDATE cars SET price = ?, stock = ?, promotion = ?,
               updated_at = datetime('now','localtime') WHERE id = ?""",
            (
                body.price if body.price is not None else current["price"],
                body.stock if body.stock is not None else current["stock"],
                body.promotion if body.promotion is not None else current["promotion"],
                car_id,
            ),
        )
        return dict(conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone())


# Static chat UI (mounted last so API routes win)
PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=int(os.getenv("PORT", "3000")))