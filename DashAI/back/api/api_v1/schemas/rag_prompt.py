from typing import Any, Dict, Optional

from pydantic import BaseModel


class RAGPromptSchema(BaseModel):
    class_name: str
    name: str
    parameters: Optional[Dict[str, Any]] = None


class RAGPromptUpdateSchema(BaseModel):
    name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
