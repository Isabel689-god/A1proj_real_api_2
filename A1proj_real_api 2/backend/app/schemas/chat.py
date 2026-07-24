from typing import Any, List, Optional

from pydantic import BaseModel


class SourceItem(BaseModel):
    title: Optional[str] = None
    source: Optional[str] = None
    score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceItem] = []
    confidence: Optional[float] = None
    provider: Optional[str] = None
    vision: Optional[dict[str, Any]] = None
    fault_localization: Optional[dict[str, Any]] = None


class ChatStreamRequest(BaseModel):
    user_id: str
    session_id: str
    question: str
    device_model: Optional[str] = None
    image_url: Optional[str] = None
