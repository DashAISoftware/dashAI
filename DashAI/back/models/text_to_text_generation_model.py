from pydantic_ai.messages import ModelMessage, ModelResponse

from DashAI.back.core.generation import from_legacy_output, to_chat_messages
from DashAI.back.models.base_generative_model import BaseGenerativeModel


class TextToTextGenerationTaskModel(BaseGenerativeModel):
    """Base class for models that generate text from a text input.

    Concrete text-to-text models must extend this class and implement
    ``generate``. Compatible with ``TextToTextGenerationTask``.
    """

    COMPATIBLE_COMPONENTS = ["TextToTextGenerationTask", "RAGTask"]

    REQUIRED_EXTRA_KWARGS = []

    def generate_result(self, messages: list[ModelMessage]) -> ModelResponse:
        """Adapt existing models to the typed text-generation interface.

        Models with structured output override this method while retaining
        ``generate`` for callers running older DashAI versions.
        """
        return from_legacy_output(self.generate(to_chat_messages(messages)))
