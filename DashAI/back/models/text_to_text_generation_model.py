from DashAI.back.core.generation import GenerationRequest, GenerationResult
from DashAI.back.models.base_generative_model import BaseGenerativeModel


class TextToTextGenerationTaskModel(BaseGenerativeModel):
    """Base class for models that generate text from a text input.

    Concrete text-to-text models must extend this class and implement
    ``generate``. Compatible with ``TextToTextGenerationTask``.
    """

    COMPATIBLE_COMPONENTS = ["TextToTextGenerationTask", "RAGTask"]

    REQUIRED_EXTRA_KWARGS = []

    def generate_result(self, request: GenerationRequest) -> GenerationResult:
        """Adapt existing models to the typed text-generation interface.

        Models with structured output override this method while retaining
        ``generate`` for callers running older DashAI versions.
        """
        return GenerationResult.from_legacy(self.generate(request.to_messages()))
