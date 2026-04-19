from typing import List


from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)
from DashAI.back.models.utils import (
    LLAMA_DEVICE_ENUM,
    LLAMA_DEVICE_PLACEHOLDER,
    LLAMA_DEVICE_TO_IDX,
)


class Phi4MiniInstructSchema(BaseSchema):
    """Schema for Phi 4 Mini Instruct model hyperparameters"""

    model_name: schema_field(
        enum_field(
            enum=[
                "unsloth/Phi-4-mini-instruct-GGUF",
            ]
        ),
        placeholder="unsloth/Phi-4-mini-instruct-GGUF",
        description=MultilingualString(
            en=("Phi-4-mini-instruct is a lightweight open model built upon synthetic "
               "data and filtered publicly available websites - with a focus on high-quality, "
               "reasoning dense data. The model belongs to the Phi-4 model family and "
               "supports 128K token context length. The model underwent an enhancement "
               "process, incorporating both supervised fine-tuning and direct preference "
               "optimization to support precise instruction adherence and robust safety "
               "measures."
            ),
            es=("Phi-4-mini-instruct es un modelo abierto ligero construido sobre datos "
               "sintéticos y sitios web disponibles públicamente filtrados, con un enfoque"
               "en datos de alta calidad y densos en razonamiento. El modelo pertenece a la "
               "familia de modelos Phi-4 y soporta un contexto de longitud de 128K tokens. "
               "El modelo se sometió a un proceso de mejora, incorporando tanto ajuste fino "
               "(fine-tuning) supervisado como optimización directa de preferencias para "
               "soportar una adherencia precisa a las instrucciones y medidas de seguridad."
            ),
        ),
        alias=MultilingualString(en="Model Name", es="Nombre del Modelo"),
    )  # type: ignore

    quantization: schema_field(
        enum_field(
            enum=[
                #"unsloth/Phi-4-mini-instruct-GGUF",
                "Phi-4-mini-instruct-Q2_K.gguf",
                "Phi-4-mini-instruct-Q2_K_L.gguf",
                "Phi-4-mini-instruct-Q3_K_M.gguf",
                "Phi-4-mini-instruct-Q4_K_M.gguf",
                "Phi-4-mini-instruct-Q5_K_M.gguf",
                "Phi-4-mini-instruct-Q6_K.gguf",
                "Phi-4-mini-instruct.BF16.gguf",
                "Phi-4-mini-instruct.Q8_0.gguf",
            ]
        ),
        placeholder="Phi-4-mini-instruct.BF16.gguf",
        description=MultilingualString(
            en=(
                "The specific Phi 4 Mini Instruct model quantization to use. Options "
                "include various quantization sizes and the BF16 format. The choice of "
                "quantization can affect the model's performance and resource usage, "
                "with smaller quantizations typically requiring less memory but "
                "potentially sacrificing some accuracy."
            ),
            es=(
                "La cuantización específica del modelo Phi 4 Mini Instruct a utilizar. "
                "Las opciones incluyen varios tamaños de cuantización y el formato BF16. "
                "La elección de la cuantización puede afectar el rendimiento y el uso de "
                "recursos del modelo, generalmente con cuantizaciones más pequeñas "
                "requieren menos memoria pero potencialmente sacrifican algo de precisión."
            ),
        ),
        alias=MultilingualString(en="Quantization", es="Cuantización"),
    )  # type: ignore

    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description=MultilingualString(
            en=(
                "Maximum number of new tokens the model will generate per response. "
                "Roughly 1 token ≈ 0.75 English words. Set to 100-200 for short "
                "answers, 500-1000 for detailed explanations or code."
            ),
            es=(
                "Número máximo de tokens nuevos que el modelo generará por respuesta. "
                "Aproximadamente 1 token ≈ 0.75 palabras en español. Use 100-200 "
                "para respuestas cortas, 500-1000 para explicaciones detalladas "
                "o código."
            ),
        ),
        alias=MultilingualString(en="Max tokens", es="Tokens máximos"),
    )  # type: ignore

    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description=MultilingualString(
            en=(
                "Sampling temperature controlling output randomness (range 0.0-1.0). "
                "At 0.0 the model picks the most likely token (deterministic). "
                "Around 0.7 balances quality and creativity. At 1.0 outputs are "
                "maximally varied."
            ),
            es=(
                "Temperatura de muestreo que controla la aleatoriedad (rango 0.0-1.0). "
                "En 0.0 el modelo elige el token más probable (determinista). "
                "Alrededor de 0.7 equilibra calidad y creatividad. En 1.0 las salidas "
                "son máximamente variadas."
            ),
        ),
        alias=MultilingualString(en="Temperature", es="Temperatura"),
    )  # type: ignore

    frequency_penalty: schema_field(
        float_field(ge=0.0, le=2.0),
        placeholder=0.1,
        description=MultilingualString(
            en=(
                "Penalizes tokens that have already appeared in the output based on "
                "frequency (range 0.0-2.0). Higher values discourage repetition."
            ),
            es=(
                "Penaliza los tokens que ya aparecieron en la salida según su "
                "frecuencia (rango 0.0-2.0). Valores más altos desincentivan "
                "la repetición."
            ),
        ),
        alias=MultilingualString(
            en="Frequency penalty", es="Penalización de frecuencia"
        ),
    )  # type: ignore

    context_window: schema_field(
        int_field(ge=1, le=131072),
        placeholder=512,
        description=MultilingualString(
            en=(
                "Total token budget for a single forward pass, including prompt and "
                "response. Mistral-7B supports up to 32K tokens; Mistral-Nemo "
                "supports up to 128K tokens."
            ),
            es=(
                "Presupuesto total de tokens por pasada, incluyendo prompt y "
                "respuesta. Mistral-7B soporta hasta 32K tokens; Mistral-Nemo "
                "soporta hasta 128K tokens."
            ),
        ),
        alias=MultilingualString(en="Context window", es="Ventana de contexto"),
    )  # type: ignore

    device: schema_field(
        enum_field(enum=LLAMA_DEVICE_ENUM),
        placeholder=LLAMA_DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Hardware device for llama.cpp inference. 'CPU' runs the model "
                "fully in RAM. A GPU option offloads all layers for faster inference."
            ),
            es=(
                "Dispositivo de hardware para inferencia con llama.cpp. 'CPU' ejecuta "
                "el modelo en RAM. Una opción de GPU descarga todas las capas para "
                "inferencia más rápida."
            ),
        ),
        alias=MultilingualString(en="Device", es="Dispositivo"),
    )  # type: ignore


class Phi4MiniInstructModel(TextToTextGenerationTaskModel):
    """Phi 4 Mini Instruct model for text generation using llama.cpp library."""

    SCHEMA = Phi4MiniInstructSchema
    COLOR: str = "#FF5733"
    DISPLAY_NAME: str = MultilingualString(
        en="Phi 4 Mini Instruct",
        es="Phi 4 Mini Instruct",
    )
    DESCRIPTION: str = MultilingualString(
        en=(
            "Phi-4-mini-instruct is a lightweight open model built upon synthetic "
            "data and filtered publicly available websites - with a focus on high-quality, "
            "reasoning dense data. The model belongs to the Phi-4 model family and "
            "supports 128K token context length. The model underwent an enhancement "
            "process, incorporating both supervised fine-tuning and direct preference "
            "optimization to support precise instruction adherence and robust safety "
            "measures."
        ),
        es=(
            "Phi-4-mini-instruct es un modelo abierto ligero construido sobre datos "
            "sintéticos y sitios web disponibles públicamente filtrados, con un enfoque"
            "en datos de alta calidad y densos en razonamiento. El modelo pertenece a la "
            "familia de modelos Phi-4 y soporta un contexto de longitud de 128K tokens. "
            "El modelo se sometió a un proceso de mejora, incorporando tanto ajuste fino "
            "(fine-tuning) supervisado como optimización directa de preferencias para "
            "soportar una adherencia precisa a las instrucciones y medidas de seguridad."
        ),
    )
        
    def __init__(self, **kwargs):
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise RuntimeError(
                "llama-cpp-python is not installed. Please install it to use QwenModel."
            ) from e

        kwargs = self.validate_and_transform(kwargs)
        self.model_name = kwargs.pop("model_name")
        self.quantization = kwargs.pop("quantization", "Phi-4-mini-instruct.Q8_0.gguf")
        self.max_tokens = kwargs.pop("max_tokens", 100)
        self.temperature = kwargs.pop("temperature", 0.7)
        self.frequency_penalty = kwargs.pop("frequency_penalty", 0.1)
        self.n_ctx = kwargs.pop("context_window", 512)

        use_gpu = LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) >= 0

        self.model = Llama.from_pretrained(
            repo_id=self.model_name,
            filename=self.quantization,
            verbose=True,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1 if use_gpu else 0,
            main_gpu=LLAMA_DEVICE_TO_IDX.get(kwargs.get("device")) if use_gpu else 0,
        )

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        output = self.model.create_chat_completion(
            messages=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
        )
        return [output["choices"][0]["message"]["content"]]
