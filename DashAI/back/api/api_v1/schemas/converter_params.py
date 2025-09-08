from typing import Any, Dict, List, Union

from pydantic import BaseModel


class ConverterParams(BaseModel):
    order: int = 0
    params: Dict[str, Union[str, int, float, bool, None]] = None
    scope: Dict[str, List[int]] = None
    target_index: int = None

    def serialize(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "params": self.params,
            "scope": self.scope,
            "target_index": self.target_index,
        }


class ConverterListParams(BaseModel):
    notebook_id: int
    converter: str
    parameters: ConverterParams
