from datetime import datetime

from beartype.typing import Union
from pydantic import BaseModel


class NotebookBase(BaseModel):
    name: Union[str, None] = None
    description: Union[str, None] = None


class NotebookCreate(NotebookBase):
    dataset_id: int


class Notebook(NotebookBase):
    id: int
    dataset_id: int
    created: datetime
    last_modified: datetime
    file_path: str
