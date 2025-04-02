from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.models.base_generative_model import BaseGenerativeModel


class ImageGenerationSchema(BaseSchema):
    """Schema for image generation models."""

    num_inference_steps: schema_field(
        int_field(ge=1),
        placeholder=5,
        description="The number of denoising steps. More steps usually lead to a higher quality image at the expense of slower inference.",
    )  # type: ignore
    guidance_scale: schema_field(
        float_field(ge=0.0),
        placeholder=7.5,
        description="Higher guidance scale encourages images that are closer to the prompt, usually at the expense of lower image quality.",
    )  # type: ignore
    device: schema_field(
        enum_field(enum=["cuda", "cpu"]),
        placeholder="cuda",
        description="Device to run the model on. CUDA is recommended for faster generation if available.",
    )  # type: ignore


class ImageGenerationModel(BaseGenerativeModel):
    """Class for models associated to ImageGenerationTasks."""

    COMPATIBLE_COMPONENTS = ["ImageGenerationTask"]
    SCHEMA = ImageGenerationSchema

    def __init__(self, **kwargs):
        """Initialize the model."""
        kwargs = self.validate_and_transform(kwargs)
        self.num_inference_steps = kwargs.pop("num_inference_steps")
        self.guidance_scale = kwargs.pop("guidance_scale")
        self.device = kwargs.pop("device")
