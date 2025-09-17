from datetime import datetime

from pydantic import BaseModel


class GenerativeSessionParameterHistorySchema(BaseModel):
    session_id: int
    parameters: dict
    modified_at: datetime
