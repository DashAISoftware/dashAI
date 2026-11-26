from typing import TYPE_CHECKING, Dict, Union

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.category.basic_preprocessing import (
    BasicPreprocessingConverter,
)
from DashAI.back.core.schema_fields import enum_field, schema_field, string_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Date

if TYPE_CHECKING:
    import pandas as pd

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

#: The layouts a start date is read in. Nothing ambiguous: "01/02/2024" could
#: be either month first.
START_FORMATS = ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")

#: The frequencies offered, as pandas aliases, with what the form shows. Each
#: one sits on the grid a forecast checks once written and read back
#: (``test_every_offered_frequency_sits_on_the_grid_a_forecast_checks``).
FREQUENCIES: Dict[str, MultilingualString] = {
    "min": MultilingualString(
        en="Every minute",
        es="Cada minuto",
        pt="A cada minuto",
        de="Jede Minute",
        zh="每分钟",
    ),
    "15min": MultilingualString(
        en="Every 15 minutes",
        es="Cada 15 minutos",
        pt="A cada 15 minutos",
        de="Alle 15 Minuten",
        zh="每 15 分钟",
    ),
    "30min": MultilingualString(
        en="Every 30 minutes",
        es="Cada 30 minutos",
        pt="A cada 30 minutos",
        de="Alle 30 Minuten",
        zh="每 30 分钟",
    ),
    "h": MultilingualString(
        en="Hourly",
        es="Por hora",
        pt="Por hora",
        de="Stündlich",
        zh="每小时",
    ),
    "D": MultilingualString(
        en="Daily",
        es="Diaria",
        pt="Diária",
        de="Täglich",
        zh="每天",
    ),
    "B": MultilingualString(
        en="Business days (Monday to Friday)",
        es="Días hábiles (lunes a viernes)",
        pt="Dias úteis (segunda a sexta)",
        de="Werktage (Montag bis Freitag)",
        zh="工作日（周一至周五）",
    ),
    "W-MON": MultilingualString(
        en="Weekly, on Mondays",
        es="Semanal, los lunes",
        pt="Semanal, às segundas-feiras",
        de="Wöchentlich, montags",
        zh="每周（周一）",
    ),
    "MS": MultilingualString(
        en="Monthly, first day of the month",
        es="Mensual, primer día del mes",
        pt="Mensal, primeiro dia do mês",
        de="Monatlich, erster Tag des Monats",
        zh="每月（月初）",
    ),
    "ME": MultilingualString(
        en="Monthly, last day of the month",
        es="Mensual, último día del mes",
        pt="Mensal, último dia do mês",
        de="Monatlich, letzter Tag des Monats",
        zh="每月（月末）",
    ),
    "QS": MultilingualString(
        en="Quarterly, first day of the quarter",
        es="Trimestral, primer día del trimestre",
        pt="Trimestral, primeiro dia do trimestre",
        de="Vierteljährlich, erster Tag des Quartals",
        zh="每季度（季初）",
    ),
    "QE": MultilingualString(
        en="Quarterly, last day of the quarter",
        es="Trimestral, último día del trimestre",
        pt="Trimestral, último dia do trimestre",
        de="Vierteljährlich, letzter Tag des Quartals",
        zh="每季度（季末）",
    ),
    "YS": MultilingualString(
        en="Yearly, January 1",
        es="Anual, 1 de enero",
        pt="Anual, 1º de janeiro",
        de="Jährlich, 1. Januar",
        zh="每年（1 月 1 日）",
    ),
    "YE": MultilingualString(
        en="Yearly, December 31",
        es="Anual, 31 de diciembre",
        pt="Anual, 31 de dezembro",
        de="Jährlich, 31. Dezember",
        zh="每年（12 月 31 日）",
    ),
}

#: A forecast infers the frequency from the dates, and it takes three.
MIN_ROWS = 3


class DateRangeSchema(BaseSchema):
    """Schema for DateRangeConverter hyperparameters."""

    start_date: schema_field(
        string_field(),
        "2024-01-01",
        description=MultilingualString(
            en=(
                "The date of the first row of the file, as YYYY-MM-DD or "
                "YYYY-MM-DD HH:MM[:SS]. It has to fall on the frequency's "
                "grid: the last day of the month for the monthly one at the "
                "end of the month, a Monday for the weekly one."
            ),
            es=(
                "La fecha de la primera fila del archivo, como AAAA-MM-DD o "
                "AAAA-MM-DD HH:MM[:SS]. Tiene que caer en la grilla de la "
                "frecuencia: el último día del mes para la mensual a fin de "
                "mes, un lunes para la semanal."
            ),
            pt=(
                "A data da primeira linha do arquivo, como AAAA-MM-DD ou "
                "AAAA-MM-DD HH:MM[:SS]. Ela precisa cair na grade da "
                "frequência: o último dia do mês para a mensal no fim do mês, "
                "uma segunda-feira para a semanal."
            ),
            de=(
                "Das Datum der ersten Zeile der Datei, als JJJJ-MM-TT oder "
                "JJJJ-MM-TT HH:MM[:SS]. Es muss auf dem Raster der Frequenz "
                "liegen: der letzte Tag des Monats für die monatliche zum "
                "Monatsende, ein Montag für die wöchentliche."
            ),
            zh=(
                "文件第一行的日期，格式为 YYYY-MM-DD 或 YYYY-MM-DD HH:MM[:SS]。"
                "它必须落在频率的网格上：月末频率需为当月最后一天，每周频率需为星期一。"
            ),
        ),
        alias=MultilingualString(
            en="Start date",
            es="Fecha de inicio",
            pt="Data de início",
            de="Startdatum",
            zh="开始日期",
        ),
    )  # type: ignore
    frequency: schema_field(
        enum_field(list(FREQUENCIES), labels=FREQUENCIES),
        "D",
        description=MultilingualString(
            en="The step between two rows.",
            es="El paso entre dos filas.",
            pt="O passo entre duas linhas.",
            de="Der Schritt zwischen zwei Zeilen.",
            zh="两行之间的步长。",
        ),
        alias=MultilingualString(
            en="Frequency",
            es="Frecuencia",
            pt="Frequência",
            de="Frequenz",
            zh="频率",
        ),
    )  # type: ignore
    column_name: schema_field(
        string_field(),
        "date",
        description=MultilingualString(
            en=(
                "The name of the new date column. If the dataset already has "
                "a column with that name, the new one is numbered: date_1."
            ),
            es=(
                "El nombre de la nueva columna de fechas. Si el dataset ya "
                "tiene una columna con ese nombre, la nueva se numera: date_1."
            ),
            pt=(
                "O nome da nova coluna de datas. Se o dataset já tiver uma "
                "coluna com esse nome, a nova é numerada: date_1."
            ),
            de=(
                "Der Name der neuen Datumsspalte. Hat der Datensatz schon "
                "eine Spalte mit diesem Namen, wird die neue nummeriert: "
                "date_1."
            ),
            zh="新日期列的名称。如果数据集中已有同名列，新列会被编号：date_1。",
        ),
        alias=MultilingualString(
            en="Column name",
            es="Nombre de la columna",
            pt="Nome da coluna",
            de="Spaltenname",
            zh="列名",
        ),
    )  # type: ignore


class DateRangeConverter(BasicPreprocessingConverter, BaseConverter):
    """Date the rows of a dataset that only holds a series of values.

    A forecasting task reads its time index from a ``Date`` column, so a file
    with the values alone cannot be forecast. This converter adds that
    column: the first row gets the start date and every following row the
    next period of the frequency, with ``pandas.date_range``.

    It dates the rows **in the order they come in the file**, and nothing can
    check that this is their order in time, or that no period is missing.
    That is the user's to know, and the description says so. Nothing is
    sorted or filled: the rows stay as they are, and the dataset gains one
    column.

    The frequency is one of ``FREQUENCIES``, each of which sits on the grid a
    forecast checks (``validate_grid``) once written in the stored format and
    read back. A start off the frequency's anchor and fewer rows than a
    frequency can be inferred from are refused, never corrected.

    It only runs in a notebook (``NOTEBOOK_ONLY``): a session transforms each
    split on its own, and each would start again at the start date. It reads
    no column (``input_cardinality`` exact 0). A notebook hands an empty
    scope over as every column, so ``transform`` returns them unchanged next
    to the new one, and numbers the new name itself: the merge only numbers
    names outside the scope.
    """

    SCHEMA = DateRangeSchema
    LEARNS_FROM_DATA = False
    NOTEBOOK_ONLY = True
    DESCRIPTION = MultilingualString(
        en=(
            "Adds a date column to a dataset that only holds values: the "
            "first row gets the start date and each following row the next "
            "period of the frequency. Use it only if the rows are already in "
            "time order, one per period and with no period missing: the "
            "converter cannot check it and dates the rows as they come. Reads "
            "no column and only runs in a notebook."
        ),
        es=(
            "Agrega una columna de fechas a un dataset que solo trae valores: "
            "la primera fila recibe la fecha de inicio y cada fila siguiente "
            "el período siguiente de la frecuencia. Úsalo solo si las filas "
            "ya están en orden temporal, una por período y sin períodos "
            "faltantes: el conversor no puede comprobarlo y fecha las filas "
            "tal como vienen. No lee ninguna columna y solo funciona en un "
            "cuaderno."
        ),
        pt=(
            "Adiciona uma coluna de datas a um dataset que só traz valores: "
            "a primeira linha recebe a data de início e cada linha seguinte "
            "o período seguinte da frequência. Use-o só se as linhas já "
            "estiverem em ordem temporal, uma por período e sem períodos "
            "faltando: o conversor não pode verificar isso e data as linhas "
            "como vêm. Não lê nenhuma coluna e só funciona em um caderno."
        ),
        de=(
            "Fügt einem Datensatz, der nur Werte enthält, eine Datumsspalte "
            "hinzu: Die erste Zeile erhält das Startdatum, jede folgende "
            "Zeile den nächsten Zeitraum der Frequenz. Nur verwenden, wenn "
            "die Zeilen schon zeitlich geordnet sind, eine pro Zeitraum und "
            "ohne fehlende Zeiträume: Der Converter kann das nicht prüfen "
            "und datiert die Zeilen so, wie sie kommen. Liest keine Spalte "
            "und läuft nur in einem Notizbuch."
        ),
        zh=(
            "为只有数值的数据集添加日期列：第一行为开始日期，之后每一行为频率的"
            "下一个周期。仅当各行已按时间顺序排列、每个周期一行且没有缺失周期时"
            "才使用：转换器无法检查这一点，会按行的原有顺序标注日期。"
            "不读取任何列，且只能在笔记本中运行。"
        ),
    )
    SHORT_DESCRIPTION = MultilingualString(
        en="Dates the rows in the order they come, from a start date.",
        es="Fecha las filas en el orden en que vienen, desde una fecha de inicio.",
        pt="Data as linhas na ordem em que vêm, a partir de uma data de início.",
        de="Datiert die Zeilen in ihrer Reihenfolge ab einem Startdatum.",
        zh="从开始日期起，按行的原有顺序标注日期。",
    )
    DISPLAY_NAME = MultilingualString(
        en="Date Range",
        es="Rango de Fechas",
        pt="Intervalo de Datas",
        de="Datumsbereich",
        zh="日期范围",
    )

    metadata = {"input_cardinality": {"exact": 0}}

    def __init__(
        self,
        start_date: str = "2024-01-01",
        frequency: str = "D",
        column_name: str = "date",
    ):
        """Keep the three settings; ``fit`` checks them.

        Parameters
        ----------
        start_date : str, optional
            The date of the first row, as ``YYYY-MM-DD`` or
            ``YYYY-MM-DD HH:MM[:SS]``. Defaults to ``"2024-01-01"``.
        frequency : str, optional
            One of ``FREQUENCIES``. Defaults to ``"D"``.
        column_name : str, optional
            The name of the new column. Defaults to ``"date"``.
        """
        super().__init__()
        self.start_date = start_date
        self.frequency = frequency
        self.column_name = column_name
        self._start = None
        self._offset = None
        self._format = None

    def fit(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> "DateRangeConverter":
        """Check the start date, the frequency and the name.

        Parameters
        ----------
        x : DashAIDataset
            Ignored: the converter reads no column.
        y : DashAIDataset, optional
            Ignored. Defaults to None.

        Returns
        -------
        DateRangeConverter
            The fitted converter instance (self).

        Raises
        ------
        ValueError
            If the start date is not in one of ``START_FORMATS``, the
            frequency is not one of ``FREQUENCIES``, the start does not fall
            on the frequency's anchor, or the name is empty.
        """
        import pandas as pd

        from DashAI.back.tasks.time_grid import sample_dates

        self._start = _parse_start(self.start_date)
        if self.frequency not in FREQUENCIES:
            raise ValueError(
                f"'frequency' must be one of {list(FREQUENCIES)}, got "
                f"'{self.frequency}'."
            )
        self._offset = pd.tseries.frequencies.to_offset(self.frequency)

        if not self._offset.is_on_offset(self._start):
            following = self._offset.rollforward(self._start)
            raise ValueError(
                f"With frequency '{self.frequency}' every date falls on its "
                f"anchor, and {sample_dates([self._start])} is not one. The "
                f"next one is {sample_dates([pd.Timestamp(following)])}: "
                "start there or pick another frequency."
            )
        if not str(self.column_name or "").strip():
            raise ValueError("The new column needs a name.")
        return self

    def transform(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> "DashAIDataset":
        """Add the date column next to the columns of ``x``, unchanged.

        Parameters
        ----------
        x : DashAIDataset
            The rows to date, in file order. Its columns come back as they
            are.
        y : DashAIDataset, optional
            Ignored. Defaults to None.

        Returns
        -------
        DashAIDataset
            ``x`` with one more column: a ``Date`` stored as text in the
            format the dates need.

        Raises
        ------
        ValueError
            If there are fewer rows than a frequency can be inferred from, or
            the dates reach past the last one pandas holds.
        """
        import pandas as pd
        import pyarrow as pa
        from pandas.errors import OutOfBoundsDatetime

        from DashAI.back.converters.dataset_columns import plan_new_column_names
        from DashAI.back.dataloaders.classes.dashai_dataset import modify_table
        from DashAI.back.tasks.time_grid import sample_dates

        n_rows = len(x)
        if n_rows == 0:
            raise ValueError("The dataset has no rows to date.")
        if n_rows < MIN_ROWS:
            raise ValueError(
                "A forecast infers the frequency from the dates, which takes "
                f"at least {MIN_ROWS} rows; this dataset has {n_rows}."
            )

        try:
            dates = pd.date_range(self._start, periods=n_rows, freq=self._offset)
        except (OutOfBoundsDatetime, OverflowError) as e:
            raise ValueError(
                f"{n_rows} steps of '{self.frequency}' from "
                f"{sample_dates([self._start])} reach past "
                f"{pd.Timestamp.max:%Y-%m-%d}, the last date pandas holds: "
                "start earlier or use a coarser frequency."
            ) from e

        self._format = _format_for(dates)
        name = plan_new_column_names(x.column_names, [self.column_name])[
            self.column_name
        ]
        return modify_table(
            x,
            {name: pa.array(list(dates.strftime(self._format)), type=pa.string())},
            types={**x.types, name: self.get_output_type()},
        )

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """The new column's type: a ``Date`` stored as text, with its format.

        Parameters
        ----------
        column_name : str, optional
            Ignored: the converter adds one column. Defaults to None.

        Returns
        -------
        DashAIDataType
            ``Date`` with the format ``transform`` chose, or the default one
            before it ran.
        """
        import pyarrow as pa

        from DashAI.back.types.date_utils import DEFAULT_DATE_FORMAT

        return Date(arrow_type=pa.string(), format=self._format or DEFAULT_DATE_FORMAT)


def _parse_start(text: str) -> "pd.Timestamp":
    """Read a start date in one of ``START_FORMATS``, and nothing else."""
    from datetime import datetime

    import pandas as pd

    stripped = str(text or "").strip()
    for layout in START_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(stripped, layout))
        except ValueError:
            continue
    raise ValueError(
        f"Start date '{text}' is not in the form YYYY-MM-DD or YYYY-MM-DD HH:MM[:SS]."
    )


def _format_for(dates: "pd.DatetimeIndex") -> str:
    """The date alone when every date falls at midnight, the time too if not.

    The finest frequency offered is a minute, and a start date has at most
    seconds, so no date has a fraction of a second.
    """
    from DashAI.back.types.date_utils import DEFAULT_DATE_FORMAT

    if (dates == dates.normalize()).all():
        return DEFAULT_DATE_FORMAT
    return "%Y-%m-%d %H:%M:%S"
