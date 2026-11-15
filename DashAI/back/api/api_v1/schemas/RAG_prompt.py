from typing import Any, Dict, Optional

from pydantic import BaseModel


class RAGPromptSchema(BaseModel):
    """Schema for creating a RAG prompt.

    Attributes:
        class_name: Registered prompt component class name.
        name: Human-readable name for the prompt.
        parameters: Optional configuration dict including template(s).
    """

    class_name: str
    name: str
    parameters: Optional[Dict[str, Any]] = None


class RAGPromptUpdateSchema(BaseModel):
    """Schema for editing a prompt saved in the library.

    Attributes:
        name: New display name. ``None`` keeps the stored name.
        parameters: New configuration including template(s). ``None`` keeps the
            stored parameters.
    """

    name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class RAGPromptForkSchema(BaseModel):
    """Schema for creating a user-owned copy of a prompt.

    Attributes:
        name: Name for the new prompt.
        parameters: Optional configuration override. ``None`` reuses the source
            prompt's content.
    """

    name: str
    parameters: Optional[Dict[str, Any]] = None
