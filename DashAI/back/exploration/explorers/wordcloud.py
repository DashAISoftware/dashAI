import base64
import os
import pathlib

from beartype.typing import Any, Dict
from PIL.Image import Image
from wordcloud import STOPWORDS, WordCloud

from DashAI.back.core.schema_fields import (
    int_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import (  # ClassLabel, Value,
    DashAIDataset,
)
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.exploration.base_explorer import BaseExplorer, BaseExplorerSchema


class WordcloudSchema(BaseExplorerSchema):
    max_words: schema_field(
        t=int_field(gt=0),
        placeholder=200,
        description="The maximum number of words to display in the wordcloud.",
    )  # type: ignore
    background_color: schema_field(
        t=none_type(string_field()),
        placeholder=None,
        description=(
            "The background color of the wordcloud. "
            "If None, the background will be transparent."
        ),
    )  # type: ignore


class WordcloudExplorer(BaseExplorer):
    """
    WordcloudExplorer is an explorer that generates a wordcloud
    from the concatenated strings of all selected columns in the dataset.
    """

    DISPLAY_NAME = "Word Cloud"
    DESCRIPTION = (
        "A wordcloud is a visual representation of text data, "
        "where the size of each word indicates its frequency in the text."
        "\n"
        "This explorer generates a wordcloud from the concatenated "
        "strings of all selected columns in the dataset."
    )

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

    def save_exploration(
        self,
        __exploration_info__: Exploration,
        explorer_info: Explorer,
        save_path: pathlib.Path,
        result: Image,
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
