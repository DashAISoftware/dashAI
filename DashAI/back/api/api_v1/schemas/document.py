from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_hash: str
    created: datetime
    optional_metadata: Optional[Dict[str, Any]]
    related_sessions: List[int] | None
    file_url: str