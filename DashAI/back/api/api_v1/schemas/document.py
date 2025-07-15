from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    id: int
    file_name: str
    optional_metadata: Optional[dict]
    created: datetime
    file_hash: str

class DocumentResponse(BaseModel):
    id: int
    file_name: str
    created: datetime
    optional_metadata: Optional[Dict[str, Any]]
    file_url: str

    class Config:
        orm_mode = True
