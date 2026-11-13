from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class GenerativeSessionParams(BaseModel):
    model_name: str
    task_name: str
    parameters: dict
    name: str
    description: Union[str, None] = None
    #: Optional slot-path to prompt-input map. When present its entries win
    #: over prompts embedded in ``parameters``.
    prompts: Optional[Dict[str, Any]] = None


class GenerativeSessionBulkDeleteParams(BaseModel):
    ids: List[int]


class GenerativeSessionExportParams(BaseModel):
    include_conversation: bool = False
