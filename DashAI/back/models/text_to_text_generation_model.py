from pydantic_ai.messages import ModelMessage, ModelResponse

from DashAI.back.core.generation import (
    from_chat_messages,
    from_legacy_output,
    text_answer,
    to_chat_messages,
)
from DashAI.back.models.base_generative_model import BaseGenerativeModel


class TextToTextGenerationTaskModel(BaseGenerativeModel):
    """Base class for models that generate text from a text input.

    New text models should override ``generate_result`` and return a native Pydantic
    AI ``ModelResponse``; ``generate`` then needs no implementation. Existing models
    that only implement ``generate`` (returning ``List[str]``) keep working. A model
    must override at least one of the two. Compatible with ``TextToTextGenerationTask``.
    """

    COMPATIBLE_COMPONENTS = ["TextToTextGenerationTask", "RAGTask"]

    REQUIRED_EXTRA_KWARGS = []

    def generate(self, messages: list[dict[str, str]]) -> list[str]:
        """Legacy entry point; by default it returns the answer of ``generate_result``.

        Override only to keep the plain ``List[str]`` contract for older hosts and
        custom legacy tasks.
        """
        if type(self).generate_result is TextToTextGenerationTaskModel.generate_result:
            raise NotImplementedError("Implement generate_result (or generate).")
        return [text_answer(self.generate_result(from_chat_messages(messages)))]

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
        if type(self).generate is TextToTextGenerationTaskModel.generate:
            raise NotImplementedError("Implement generate_result (or generate).")
        return from_legacy_output(self.generate(to_chat_messages(messages)))
