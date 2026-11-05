from pydantic_ai.messages import ModelMessage, ModelResponse

from DashAI.back.core.generation import from_legacy_output, to_chat_messages
from DashAI.back.models.base_generative_model import BaseGenerativeModel


class TextToTextGenerationTaskModel(BaseGenerativeModel):
    """Base class for models that generate text from a text input.

    New text models should override ``generate_result`` and return a native Pydantic
    AI ``ModelResponse``. Keep a working ``generate`` too (it returns ``List[str]``):
    older hosts and custom legacy tasks still call it, and the default
    ``generate_result`` is built on it. Compatible with ``TextToTextGenerationTask``.
    """

    COMPATIBLE_COMPONENTS = ["TextToTextGenerationTask", "RAGTask"]

    REQUIRED_EXTRA_KWARGS = []

    def generate_result(self, messages: list[ModelMessage]) -> ModelResponse:
        """Adapt existing models to the typed text-generation interface.

        New models must override this method and return a native ``ModelResponse``
        directly, while retaining ``generate`` for older hosts.

        Warnings
        --------
        This default implementation is a compatibility fallback for existing
        plugins only. Do not rely on it or its legacy conversion helpers when
        implementing a new model; use the native Pydantic AI contract instead.
        """
        return from_legacy_output(self.generate(to_chat_messages(messages)))
