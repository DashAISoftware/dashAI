from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    file_name: str
    file_hash: str
    created: datetime
    optional_metadata: Optional[Dict[str, Any]]
    related_sessions: List[int]|None
    file_url: str

    class Config:
        orm_mode = True
