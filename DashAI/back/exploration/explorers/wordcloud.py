import base64
import os
import pathlib

from beartype.typing import Any, Dict

from DashAI.back.core.schema_fields import (
    int_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorerSchema
from DashAI.back.exploration.distribution_explorer import DistributionExplorer


class WordcloudSchema(BaseExplorerSchema):
    max_words: schema_field(
        t=int_field(gt=0),
        placeholder=200,
        description=MultilingualString(
            en="Maximum number of words to display in the word cloud.",
            es="Número máximo de palabras a mostrar en la nube de palabras.",
        ),
        alias=MultilingualString(en="Max words", es="Máximo de palabras"),
    )  # type: ignore
    background_color: schema_field(
        t=none_type(string_field()),
        placeholder=None,
        description=MultilingualString(
            en=(
                "Background color of the word cloud. If None, the background is "
                "transparent."
            ),
            es=(
                "Color de fondo de la nube de palabras. Si es None, el fondo es "
                "transparente."
            ),
        ),
        alias=MultilingualString(
            en="Background color",
            es="Color de fondo",
        ),
    )  # type: ignore


class WordcloudExplorer(DistributionExplorer):
    """
    WordcloudExplorer is an explorer that generates a wordcloud
    from the concatenated strings of all selected columns in the dataset.
    """

    DISPLAY_NAME = MultilingualString(en="Word Cloud", es="Nube de Palabras")
    DESCRIPTION = MultilingualString(
        en=(
            "Visual representation of text where word size reflects frequency. "
            "Generates a word cloud by concatenating selected text columns."
        ),
        es=(
            "Representación visual del texto donde el tamaño de la palabra "
            "refleja su frecuencia. Genera una nube de palabras concatenando "
            "columnas de texto seleccionadas."
        ),
    )
    IMAGE_PREVIEW = "wordcloud.png"

    SCHEMA = WordcloudSchema
    metadata: Dict[str, Any] = {
        "allowed_dtypes": ["string"],
        "restricted_dtypes": [],
        "input_cardinality": {"min": 1},
    }

    def __init__(self, **kwargs) -> None:
        self.max_words = kwargs.get("max_words", 200)
        self.background_color = kwargs.get("background_color")
        super().__init__(**kwargs)

    def launch_exploration(self, dataset: DashAIDataset, explorer_info: Explorer):
        from wordcloud import STOPWORDS, WordCloud

        _df = dataset.to_pandas()
        cols = [col["columnName"] for col in explorer_info.columns]

        # concatenate all columns into one string
        text = " ".join(_df[cols].astype(str).sum(axis=1))

        # create wordcloud
        wordcloud = WordCloud(
            max_words=self.max_words,
            stopwords=STOPWORDS,
            background_color=self.background_color,
            mode="RGBA" if self.background_color is None else "RGB",
            width=800,
            height=600,
        ).generate(text)

        return wordcloud.to_image()

    def save_notebook(
        self,
        __exploration_info__: Notebook,
        explorer_info: Explorer,
        save_path: pathlib.Path,
        result: Any,
    ) -> str:
        filename = f"{explorer_info.id}.png"
        path = pathlib.Path(os.path.join(save_path, filename))
        result.save(path, format="PNG")

        return path.as_posix()

    def get_results(
        self, exploration_path: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        resultType = "image_base64"
        config = {}

        # Load image
        with open(exploration_path, "rb") as f:
            result = f.read()

        # encode image to base64
        result = base64.b64encode(result).decode("utf-8")

        # Return image
        return {"data": result, "type": resultType, "config": config}
