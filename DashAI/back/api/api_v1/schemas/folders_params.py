from datetime import datetime

from pydantic import BaseModel


class FolderCreateParams(BaseModel):
    name: str


class FolderUpdateParams(BaseModel):
    name: str


class Folder(BaseModel):
    id: int
    name: str
    created: datetime
    last_modified: datetime

    class Config:
        from_attributes = True
