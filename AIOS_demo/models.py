from pydantic import BaseModel
from typing import List, Optional

class KnowledgeAssetCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = []

class KnowledgeAsset(KnowledgeAssetCreate):
    id: int
    created_at: str

class SearchResult(BaseModel):
    id: int
    title: str
    content: str
    tags: List[str]
    score: float
    rerank_score: Optional[float] = None

class AskRequest(BaseModel):
    query: str

class AskResponse(BaseModel):
    answer: str
    sources: List[dict]
    trace: dict
