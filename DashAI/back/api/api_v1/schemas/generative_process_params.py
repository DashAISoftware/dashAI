from pydantic import BaseModel


class GenerativeProcessParams(BaseModel):
    input: str
    session_id: int
