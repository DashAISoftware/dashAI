"""OpenML dataset exporter for DashAI."""

from typing import TYPE_CHECKING, Any, Final

from DashAI.back.core.schema_fields import (
    enum_field,
    list_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataset_exporters.base_dataset_exporter import (
    BaseDatasetExporter,
    BaseDatasetExportSchema,
    ExportPayload,
    ExportResult,
)
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.dashai_image import DashAIImage
from DashAI.back.types.value_types import (
    Binary,
    Date,
    Decimal,
    Duration,
    Time,
    Timestamp,
)

if TYPE_CHECKING:
    import pandas as pd

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

#: DashAI types OpenML cannot store; these columns are left out of the upload.
_UNSUPPORTED_TYPES: Final = (DashAIImage, Binary)
#: DashAI types sent to OpenML as text, since ARFF has no native equivalent.
_TEXT_TYPES: Final = (Date, Time, Timestamp, Duration)

#: Licences offered by the OpenML upload form.
OPENML_LICENCES: Final = [
    "Public",
    "CC0",
    "CC-BY",
    "CC-BY-SA",
    "CC-BY-ND",
    "CC-BY-NC",
    "CC-BY-NC-SA",
    "CC-BY-NC-ND",
]


class OpenMLExportSchema(BaseDatasetExportSchema):
    """Parameters required to publish a dataset on OpenML."""

    default_target_attribute: schema_field(
        string_field(),
        "",
        description=MultilingualString(
            en="Column that OpenML tasks will use as the prediction target.",
            es="Columna que las tareas de OpenML usarán como objetivo a predecir.",
            pt="Coluna que as tarefas do OpenML usarão como alvo da predição.",
            de="Spalte, die OpenML-Aufgaben als Vorhersageziel verwenden.",
            zh="OpenML 任务将用作预测目标的列。",
        ),
        alias=MultilingualString(
            en="Target column",
            es="Columna objetivo",
            pt="Coluna alvo",
            de="Zielspalte",
            zh="目标列",
        ),
    )  # type: ignore
    licence: schema_field(
        enum_field(OPENML_LICENCES),
        "CC0",
        description=MultilingualString(
            en="Licence under which the dataset is published.",
            es="Licencia bajo la cual se publica el dataset.",
            pt="Licença sob a qual o conjunto de dados é publicado.",
            de="Lizenz, unter der der Datensatz veröffentlicht wird.",
            zh="发布数据集所使用的许可证。",
        ),
        alias=MultilingualString(
            en="Licence", es="Licencia", pt="Licença", de="Lizenz", zh="许可证"
        ),
    )  # type: ignore
    creator: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="People or organization that created the data.",
            es="Personas u organización que crearon los datos.",
            pt="Pessoas ou organização que criaram os dados.",
            de="Personen oder Organisation, die die Daten erstellt haben.",
            zh="创建这些数据的人员或组织。",
        ),
        alias=MultilingualString(
            en="Creator", es="Creador", pt="Criador", de="Ersteller", zh="创建者"
        ),
    )  # type: ignore
    contributor: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="People or organizations that contributed to the data.",
            es="Personas u organizaciones que contribuyeron a los datos.",
            pt="Pessoas ou organizações que contribuíram para os dados.",
            de="Personen oder Organisationen, die zu den Daten beigetragen haben.",
            zh="为这些数据做出贡献的人员或组织。",
        ),
        alias=MultilingualString(
            en="Contributor",
            es="Colaborador",
            pt="Colaborador",
            de="Mitwirkende",
            zh="贡献者",
        ),
    )  # type: ignore
    collection_date: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Date or period when the data was collected, for example 2024.",
            es="Fecha o periodo en que se recolectaron los datos, por ejemplo 2024.",
            pt="Data ou período em que os dados foram coletados, por exemplo 2024.",
            de="Datum oder Zeitraum der Datenerhebung, zum Beispiel 2024.",
            zh="数据收集的日期或时期，例如 2024。",
        ),
        alias=MultilingualString(
            en="Collection date",
            es="Fecha de recolección",
            pt="Data de coleta",
            de="Erhebungsdatum",
            zh="收集日期",
        ),
    )  # type: ignore
    language: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Language of the data, in English, for example Spanish.",
            es="Idioma de los datos, en inglés, por ejemplo Spanish.",
            pt="Idioma dos dados, em inglês, por exemplo Spanish.",
            de="Sprache der Daten auf Englisch, zum Beispiel Spanish.",
            zh="数据的语言（用英文填写），例如 Spanish。",
        ),
        alias=MultilingualString(
            en="Language", es="Idioma", pt="Idioma", de="Sprache", zh="语言"
        ),
    )  # type: ignore
    ignore_attribute: schema_field(
        none_type(list_field(string_field())),
        None,
        description=MultilingualString(
            en="Columns that OpenML tasks should not use as features, such as IDs.",
            es=(
                "Columnas que las tareas de OpenML no deben usar como atributos, "
                "como identificadores."
            ),
            pt=(
                "Colunas que as tarefas do OpenML não devem usar como atributos, "
                "como identificadores."
            ),
            de=(
                "Spalten, die OpenML-Aufgaben nicht als Merkmale verwenden sollen, "
                "zum Beispiel IDs."
            ),
            zh="OpenML 任务不应用作特征的列，例如 ID。",
        ),
        alias=MultilingualString(
            en="Ignored columns",
            es="Columnas ignoradas",
            pt="Colunas ignoradas",
            de="Ignorierte Spalten",
            zh="忽略的列",
        ),
    )  # type: ignore
    citation: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="How to cite the dataset or the work that produced it.",
            es="Cómo citar el dataset o el trabajo que lo produjo.",
            pt="Como citar o conjunto de dados ou o trabalho que o produziu.",
            de="Wie der Datensatz oder die zugrunde liegende Arbeit zitiert wird.",
            zh="如何引用该数据集或产生它的工作。",
        ),
        alias=MultilingualString(
            en="Citation", es="Cita", pt="Citação", de="Zitation", zh="引用"
        ),
    )  # type: ignore
    original_data_url: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en="Link to the original source of the data, if any.",
            es="Enlace a la fuente original de los datos, si existe.",
            pt="Link para a fonte original dos dados, se houver.",
            de="Link zur ursprünglichen Datenquelle, falls vorhanden.",
            zh="数据原始来源的链接（如有）。",
        ),
        alias=MultilingualString(
            en="Original data URL",
            es="URL de los datos originales",
            pt="URL dos dados originais",
            de="URL der Originaldaten",
            zh="原始数据链接",
        ),
    )  # type: ignore


class OpenMLDatasetExporter(BaseDatasetExporter):
    """Dataset exporter that publishes DashAI datasets to OpenML.

    Requires an OpenML API key. Uploads go to the server set in the
    ``OPENML_SERVER`` setting, which defaults to the OpenML test server.
    """

    DISPLAY_NAME: Final = MultilingualString(
        en="OpenML",
        es="OpenML",
        zh="OpenML",
        de="OpenML",
        pt="OpenML",
    )
    DESCRIPTION: Final = MultilingualString(
        en=(
            "Publish the dataset on OpenML, an open platform for reproducible "
            "machine learning research, so others can find it, download it and "
            "use it in benchmarks."
        ),
        es=(
            "Publica el dataset en OpenML, una plataforma abierta para la "
            "investigación reproducible en aprendizaje automático, para que otras "
            "personas puedan encontrarlo, descargarlo y usarlo en benchmarks."
        ),
        zh="将数据集发布到 OpenML（一个用于可重现机器学习研究的开放平台），"
        "让其他人能够找到、下载并在基准测试中使用它。",
        de=(
            "Veröffentlicht den Datensatz auf OpenML, einer offenen Plattform für "
            "reproduzierbare Forschung im maschinellen Lernen, damit andere ihn "
            "finden, herunterladen und in Benchmarks verwenden können."
        ),
        pt=(
            "Publica o conjunto de dados no OpenML, uma plataforma aberta para "
            "pesquisa reproduzível em aprendizado de máquina, para que outras "
            "pessoas possam encontrá-lo, baixá-lo e usá-lo em benchmarks."
        ),
    )
    SCHEMA = OpenMLExportSchema
    REQUIRED_CREDENTIALS = ["OpenMLCredential"]
    SOURCE_NAME = "OpenMLDatasetSource"

    def validate(self, dataset: "DashAIDataset", params: dict[str, Any]) -> list[str]:
        """Check the base rules plus the OpenML column references.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to export.
        params : dict[str, Any]
            Export parameters, already validated against :attr:`SCHEMA`.

        Returns
        -------
        list[str]
            Validation errors. An empty list means the export can proceed.
        """
        errors = super().validate(dataset, params)
        columns = set(dataset.column_names)

        target = params.get("default_target_attribute", "")
        if target not in columns:
            errors.append(f"The target column '{target}' is not in the dataset.")
        elif target in _unsupported_columns(dataset):
            errors.append(
                f"The target column '{target}' has a type OpenML cannot store."
            )

        ignored = params.get("ignore_attribute") or []
        missing = [col for col in ignored if col not in columns]
        if missing:
            errors.append(f"The ignored columns {missing} are not in the dataset.")
        if target in ignored:
            errors.append("The target column cannot also be an ignored column.")
        return errors

    def prepare(
        self, dataset: "DashAIDataset", params: dict[str, Any], temp_path: str
    ) -> ExportPayload:
        """Build the OpenML dataset object from a DashAI dataset.

        Image and binary columns are left out because OpenML cannot store
        them. Categorical columns become nominal attributes, which OpenML
        needs for classification targets.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to export.
        params : dict[str, Any]
            Export parameters, already validated against :attr:`SCHEMA`.
        temp_path : str
            Unused: ``openml`` serializes the dataset itself when publishing.

        Returns
        -------
        ExportPayload
            ``metadata["openml_dataset"]`` holds the ``OpenMLDataset`` to
            publish and ``metadata["dropped_columns"]`` the columns left out.
        """
        import openml

        dropped = _unsupported_columns(dataset)
        dataframe = _to_openml_dataframe(dataset, dropped)
        ignored = [
            col for col in params.get("ignore_attribute") or [] if col not in dropped
        ]

        openml_dataset = openml.datasets.create_dataset(
            name=params["name"],
            description=params["description"],
            creator=_optional_text(params, "creator"),
            contributor=_optional_text(params, "contributor"),
            collection_date=_optional_text(params, "collection_date"),
            language=_optional_text(params, "language"),
            licence=params["licence"],
            attributes="auto",
            data=dataframe,
            default_target_attribute=params["default_target_attribute"],
            ignore_attribute=ignored or None,
            citation=_optional_text(params, "citation"),
            original_data_url=_optional_text(params, "original_data_url"),
        )
        return ExportPayload(
            metadata={"openml_dataset": openml_dataset, "dropped_columns": dropped}
        )

    def upload(self, payload: ExportPayload, params: dict[str, Any]) -> ExportResult:
        """Publish the prepared dataset with the stored OpenML API key.

        Parameters
        ----------
        payload : ExportPayload
            Content returned by :meth:`prepare`.
        params : dict[str, Any]
            Export parameters, already validated against :attr:`SCHEMA`.

        Returns
        -------
        ExportResult
            OpenML dataset id and its page on the configured server.
        """
        openml_dataset = payload.metadata["openml_dataset"]
        with self.get_credential("OpenMLCredential").configured():
            openml_dataset.publish()
            url = openml_dataset.openml_url
        return ExportResult(
            remote_id=str(openml_dataset.dataset_id),
            url=url,
            detail={"dropped_columns": payload.metadata.get("dropped_columns", [])},
        )

    def get_remote_status(self, remote_id: str) -> str | None:
        """Return the OpenML status of a published dataset.

        OpenML keeps new datasets in ``in_preparation`` while it processes
        them, then marks them ``active`` (or ``deactivated``).

        Parameters
        ----------
        remote_id : str
            OpenML dataset id returned by :meth:`upload`.

        Returns
        -------
        str or None
            OpenML status, or None if the dataset is not listed.
        """
        import openml

        with self.get_credential("OpenMLCredential").configured():
            listing = openml.datasets.list_datasets(
                data_id=[int(remote_id)], status="all", output_format="dataframe"
            )
        if listing.empty:
            return None
        return str(listing.iloc[0]["status"])


def _optional_text(params: dict[str, Any], key: str) -> str | None:
    """Return an optional text parameter, or None when it is missing or blank.

    OpenML rejects empty elements in the dataset description, while ``None``
    fields are left out of it entirely.
    """
    value = params.get(key)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _unsupported_columns(dataset: "DashAIDataset") -> list[str]:
    """Return the columns whose DashAI type OpenML cannot store."""
    types = dataset.types or {}
    return [
        col
        for col in dataset.column_names
        if isinstance(types.get(col), _UNSUPPORTED_TYPES)
    ]


def _to_openml_dataframe(
    dataset: "DashAIDataset", dropped: list[str]
) -> "pd.DataFrame":
    """Convert a DashAI dataset into a DataFrame OpenML can describe.

    Parameters
    ----------
    dataset : DashAIDataset
        Dataset to convert.
    dropped : list[str]
        Columns to leave out.

    Returns
    -------
    pd.DataFrame
        Data with categorical columns as ``category`` dtype, decimals as
        floats and temporal values as text.
    """
    types = dataset.types or {}
    dataframe = dataset.to_pandas().drop(columns=dropped)
    for col in dataframe.columns:
        col_type = types.get(col)
        if isinstance(col_type, Categorical):
            values = dataframe[col]
            dataframe[col] = values.where(values.isna(), values.astype(str)).astype(
                "category"
            )
        elif isinstance(col_type, Decimal):
            dataframe[col] = dataframe[col].astype(float)
        elif isinstance(col_type, _TEXT_TYPES):
            values = dataframe[col]
            dataframe[col] = values.where(values.isna(), values.astype(str))
    return dataframe
