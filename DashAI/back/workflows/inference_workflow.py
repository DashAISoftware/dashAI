from DashAI.back.core.utils import MultilingualString
from DashAI.back.workflows.base_generative_workflow import BaseGenerativeWorkflow

INFERENCE_WORKFLOW_NAME = "InferenceWorkflow"


class InferenceWorkflow(BaseGenerativeWorkflow):
    """Run the session model directly on the task input.

    Task agnostic: the session picks the task and the model, the model's own
    schema validates the parameters and ``GenerativeJob`` runs each turn.
    """

    DISPLAY_NAME: MultilingualString = MultilingualString(
        en="Model inference",
        es="Inferencia de modelo",
        pt="Inferência de modelo",
        de="Modellinferenz",
        zh="模型推理",
    )
    DESCRIPTION: MultilingualString = MultilingualString(
        en=(
            "Run a generative model directly: chat with a language model,"
            " generate images and more."
        ),
        es=(
            "Ejecuta un modelo generativo directamente: conversa con un modelo"
            " de lenguaje, genera imágenes y más."
        ),
        pt=(
            "Execute um modelo generativo diretamente: converse com um modelo"
            " de linguagem, gere imagens e muito mais."
        ),
        de=(
            "Ein generatives Modell direkt ausführen: mit einem Sprachmodell"
            " chatten, Bilder erzeugen und mehr."
        ),
        zh="直接运行生成式模型：与语言模型对话、生成图像等。",
    )
