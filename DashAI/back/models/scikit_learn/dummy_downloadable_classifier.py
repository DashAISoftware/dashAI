import time
from typing import Optional

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.downloads.downloadable import (
    DownloadableMixin,
    ProgressReporter,
)
from DashAI.back.models.scikit_learn.svc import SVC


class DummyDownloadableClassifierSchema(BaseSchema):
    """Schema for the dummy classifier, exposing one nested classifier field.

    The ``nested_classifier`` parameter is a component field so a second
    (possibly download-required) tabular classifier can be selected inside
    this one, letting the nested-download flow be exercised at depth.
    """

    nested_classifier: schema_field(
        component_field(parent="TabularClassificationModel"),
        placeholder={"component": "SVC", "params": {}},
        description=MultilingualString(
            en="A nested tabular classifier, used to test nested downloads.",
            es="Un clasificador tabular anidado, para probar descargas anidadas.",
            pt="Um classificador tabular aninhado, para testar downloads aninhados.",
            de=(
                "Ein verschachtelter tabellarischer Klassifikator zum Testen "
                "verschachtelter Downloads."
            ),
            zh="嵌套的表格分类器，用于测试嵌套下载。",
        ),
        alias=MultilingualString(
            en="Nested classifier",
            es="Clasificador anidado",
            pt="Classificador aninhado",
            de="Verschachtelter Klassifikator",
            zh="嵌套分类器",
        ),
    )  # type: ignore


class DummyDownloadableClassifier(DownloadableMixin, SVC):
    """A fake download-required tabular classifier for UI testing.

    Behaves exactly like :class:`SVC` at train time but is flagged as
    requiring a download so the inline download control appears when it is
    selected as another component's parameter (e.g. the Bag-of-Words tabular
    classifier). Its ``download`` writes a marker file instead of fetching any
    real artifact, so the download/delete flow can be exercised end to end
    without network access.
    """

    SCHEMA = DummyDownloadableClassifierSchema
    DOWNLOAD_SIZE_BYTES = 256 * 1024 * 1024
    COLOR = "#B39DDB"
    ICON = "Timeline"
    DISPLAY_NAME = MultilingualString(
        en="Dummy Downloadable Classifier",
        es="Clasificador Descargable de Prueba",
        pt="Classificador Baixavel de Teste",
        de="Dummy Herunterladbarer Klassifikator",
        zh="虚拟可下载分类器",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "A test-only classifier that requires a download. It trains like an "
            "SVM but is used to preview the inline download control when picking "
            "a nested component."
        ),
        es=(
            "Un clasificador solo de prueba que requiere descarga. Entrena como "
            "una SVM, pero sirve para previsualizar el control de descarga en "
            "linea al elegir un componente anidado."
        ),
        pt=(
            "Um classificador apenas de teste que requer download. Treina como "
            "uma SVM, mas serve para pre-visualizar o controle de download em "
            "linha ao escolher um componente aninhado."
        ),
        de=(
            "Ein reiner Testklassifikator, der einen Download erfordert. Er "
            "trainiert wie eine SVM, dient aber zur Vorschau des Inline-"
            "Download-Steuerelements bei der Auswahl einer verschachtelten "
            "Komponente."
        ),
        zh=(
            "仅用于测试的分类器，需要下载。它像 SVM 一样训练，"
            "用于在选择嵌套组件时预览内联下载控件。"
        ),
    )

    def __init__(self, **kwargs):
        """Store the nested classifier and forward the rest to ``SVC``.

        Parameters
        ----------
        **kwargs : dict
            May include ``nested_classifier`` (an instantiated tabular
            classifier), which is kept as an attribute and not passed to the
            underlying sklearn estimator.
        """
        self.nested_classifier = kwargs.pop("nested_classifier", None)
        super().__init__(**kwargs)

    @classmethod
    def is_downloaded(cls) -> bool:
        """Return whether the marker file is present.

        Returns
        -------
        bool
            ``True`` when ``component_dir()`` exists and is non-empty.
        """
        directory = cls.component_dir()
        return directory.is_dir() and any(directory.iterdir())

    @classmethod
    def download(cls, report: Optional[ProgressReporter] = None) -> None:
        """Write a marker file to simulate a download.

        A short delay is inserted so the downloading state is visible in the
        UI. No real artifact is fetched.

        Parameters
        ----------
        report : ProgressReporter, optional
            Callback invoked with progress fractions and phase messages.
        """
        directory = cls.component_dir()
        directory.mkdir(parents=True, exist_ok=True)
        steps = 4
        for step in range(steps):
            if report is not None:
                report(step / steps, "Downloading dummy weights")
            time.sleep(1)
        (directory / "weights.marker").write_text("dummy", encoding="utf-8")
        if report is not None:
            report(1.0, "Done")
