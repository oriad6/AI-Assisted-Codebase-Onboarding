from fastapi import APIRouter
from pydantic import BaseModel
from services.ai import generate_content_with_fallback

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    code_context: str
    api_key: str


class ChatResponse(BaseModel):
    success: bool
    answer: str = ""
    model_used: str = ""
    error: str | None = None


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Send a question about the code and get an AI response."""
    ctx = req.code_context[:20000] + "\nQ: " + req.question
    ans, model_name = generate_content_with_fallback(ctx, req.api_key)
    if model_name == "Error":
        return ChatResponse(success=False, error=ans)
    return ChatResponse(success=True, answer=ans, model_used=model_name)
