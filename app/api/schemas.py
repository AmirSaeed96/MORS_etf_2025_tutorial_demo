"""API request and response schemas"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request schema"""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    message: str = Field(..., description="User message")
    override_routing: Literal["auto", "rag", "no_rag"] = Field(
        default="auto",
        description="Override routing decision (auto, rag, no_rag)"
    )


class MessageMetadata(BaseModel):
    """Metadata for assistant message"""
    used_rag: bool
    review_label: str
    router_path: str
    trace_id: Optional[str] = None
    context_sources: List[dict] = []
    review_confidence: Optional[float] = None
    tldr: Optional[str] = None


class AssistantMessage(BaseModel):
    """Assistant message in response"""
    role: str = "assistant"
    content: str
    metadata: MessageMetadata


class ChatResponse(BaseModel):
    """Chat response schema"""
    conversation_id: str
    message: AssistantMessage


class HealthStatus(BaseModel):
    """Health check response"""
    status: str
    ollama: bool
    chromadb: bool
    phoenix: bool
    message: Optional[str] = None
