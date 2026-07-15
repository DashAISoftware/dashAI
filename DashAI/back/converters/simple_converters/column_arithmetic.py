from typing import TYPE_CHECKING, Union

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.category.feature_engineering import (
    FeatureEngineeringConverter,
)
from DashAI.back.core.schema_fields import (
    enum_field,
    float_field,
    none_type,
    schema_field,
    string_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float, Integer

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

OPERATIONS = ["add", "subtract", "multiply", "divide"]
OPERAND_B_MODES = ["column", "constant"]


class ColumnArithmeticSchema(BaseSchema):
    """Schema for ColumnArithmetic hyperparameters."""

    column_a: schema_field(
        string_field(),
        "",
        description=MultilingualString(
            en="Name of the first operand column.",
            es="Nombre de la columna del primer operando.",
            pt="Nome da coluna do primeiro operando.",
            de="Name der ersten Operanden-Spalte.",
            zh="第一个操作数列的名称。",
        ),
    )  # type: ignore
    operand_b_mode: schema_field(
        enum_field(OPERAND_B_MODES),
        "column",
        description=MultilingualString(
            en=(
                "Whether the second operand is another column ('column') or "
                "a fixed number ('constant')."
            ),
            es=(
                "Si el segundo operando es otra columna ('column') o un "
                "número fijo ('constant')."
            ),
            pt=(
                "Se o segundo operando é outra coluna ('column') ou um "
                "número fixo ('constant')."
            ),
            de=(
                "Ob der zweite Operand eine weitere Spalte ('column') oder "
                "eine feste Zahl ('constant') ist."
            ),
            zh="第二个操作数是另一列（'column'）还是固定数值（'constant'）。",
        ),
    )  # type: ignore
    column_b: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en=(
                "Name of the second operand column. Can be the same as "
                "'column_a'. Required when 'operand_b_mode' is 'column'."
            ),
            es=(
                "Nombre de la columna del segundo operando. Puede ser la "
                "misma que 'column_a'. Requerido cuando 'operand_b_mode' es "
                "'column'."
            ),
            pt=(
                "Nome da coluna do segundo operando. Pode ser a mesma que "
                "'column_a'. Necessário quando 'operand_b_mode' é 'column'."
            ),
            de=(
                "Name der zweiten Operanden-Spalte. Kann mit 'column_a' "
                "übereinstimmen. Erforderlich, wenn 'operand_b_mode' "
                "'column' ist."
            ),
            zh="第二个操作数列的名称。可以与 'column_a' 相同。"
            "当 'operand_b_mode' 为 'column' 时必填。",
        ),
    )  # type: ignore
    constant: schema_field(
        none_type(float_field()),
        None,
        description=MultilingualString(
            en=(
                "Fixed number used as the second operand. Required when "
                "'operand_b_mode' is 'constant'."
            ),
            es=(
                "Número fijo usado como segundo operando. Requerido cuando "
                "'operand_b_mode' es 'constant'."
            ),
            pt=(
                "Número fixo usado como segundo operando. Necessário quando "
                "'operand_b_mode' é 'constant'."
            ),
            de=(
                "Feste Zahl, die als zweiter Operand verwendet wird. "
                "Erforderlich, wenn 'operand_b_mode' 'constant' ist."
            ),
            zh="用作第二个操作数的固定数值。当 'operand_b_mode' 为 'constant' 时必填。",
        ),
    )  # type: ignore
    operation: schema_field(
        enum_field(OPERATIONS),
        "add",
        description=MultilingualString(
            en=(
                "Arithmetic operation to apply between 'column_a' and the "
                "second operand ('column_b' or 'constant')."
            ),
            es=(
                "Operación aritmética a aplicar entre 'column_a' y el "
                "segundo operando ('column_b' o 'constant')."
            ),
            pt=(
                "Operação aritmética a aplicar entre 'column_a' e o "
                "segundo operando ('column_b' ou 'constant')."
            ),
            de=(
                "Arithmetische Operation zwischen 'column_a' und dem "
                "zweiten Operanden ('column_b' oder 'constant')."
            ),
            zh="在 'column_a' 与第二个操作数（'column_b' 或 'constant'）"
            "之间应用的算术运算。",
        ),
    )  # type: ignore
    output_column_name: schema_field(
        none_type(string_field()),
        None,
        description=MultilingualString(
            en=(
                "Name of the resulting column. If null, a name is generated "
                "from the operands and the operation."
            ),
            es=(
                "Nombre de la columna resultante. Si es nulo, se genera un "
                "nombre a partir de los operandos y la operación."
            ),
            pt=(
                "Nome da coluna resultante. Se nulo, um nome é gerado a "
                "partir dos operandos e da operação."
            ),
            de=(
                "Name der resultierenden Spalte. Wenn null, wird ein Name "
                "aus den Operanden und der Operation generiert."
            ),
            zh="结果列的名称。如果为空，将根据操作数和运算生成名称。",
        ),
    )  # type: ignore


class ColumnArithmetic(FeatureEngineeringConverter, BaseConverter):
    """Combine a column with a second operand into a new numeric column.

    Applies addition, subtraction, multiplication, or division element-wise
    between ``column_a`` and a second operand, which is either another
    column (``operand_b_mode="column"``, via ``column_b``) or a fixed number
    (``operand_b_mode="constant"``, via ``constant``, e.g. ``column_a * 2``).
    When using two columns, both may refer to the same one (e.g. dividing a
    column by itself). Division by zero yields ``NaN`` instead of raising an
    error.

    The original columns are left untouched; the result is appended as a new
    column named ``output_column_name``, or, if not provided,
    ``<column_a>_<operation>_<column_b>`` or ``<column_a>_<operation>_<constant>``.

    The output column is ``Integer`` when both operands are ``Integer`` (a
    whole-number ``constant`` counts as ``Integer``) and the operation is
    ``add``, ``subtract``, or ``multiply`` (all of which stay exact on
    integers). ``divide`` always produces a ``Float`` column, since integer
    division is not exact in general, and any operation involving a
    ``Float`` operand also produces a ``Float`` column.
    """

    SCHEMA = ColumnArithmeticSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Applies an arithmetic operation (add, subtract, multiply, divide) "
            "between a column and a second operand — another column or a "
            "fixed constant (e.g. column * 2) — and appends the result as a "
            "new column."
        ),
        es=(
            "Aplica una operación aritmética (sumar, restar, multiplicar, "
            "dividir) entre una columna y un segundo operando — otra "
            "columna o una constante fija (por ejemplo, columna * 2) — y "
            "agrega el resultado como una nueva columna."
        ),
        pt=(
            "Aplica uma operação aritmética (somar, subtrair, multiplicar, "
            "dividir) entre uma coluna e um segundo operando — outra "
            "coluna ou uma constante fixa (por exemplo, coluna * 2) — e "
            "adiciona o resultado como uma nova coluna."
        ),
        de=(
            "Wendet eine arithmetische Operation (Addieren, Subtrahieren, "
            "Multiplizieren, Dividieren) zwischen einer Spalte und einem "
            "zweiten Operanden an — einer weiteren Spalte oder einer festen "
            "Konstante (z. B. Spalte * 2) — und fügt das Ergebnis als neue "
            "Spalte hinzu."
        ),
        zh=(
            "对一列与第二个操作数（另一列或固定常量，例如 列 * 2）应用算术运算"
            "（加、减、乘、除），并将结果作为新列追加。"
        ),
    )
    SHORT_DESCRIPTION = MultilingualString(
        en="Arithmetic combination of a column with another column or a constant.",
        es="Combinación aritmética de una columna con otra columna o una constante.",
        pt="Combinação aritmética de uma coluna com outra coluna ou uma constante.",
        de="Arithmetische Kombination einer Spalte mit einer weiteren Spalte "
        "oder einer Konstante.",
        zh="将一列与另一列或常量进行算术组合。",
    )
    DISPLAY_NAME = MultilingualString(
        en="Column Arithmetic",
        es="Aritmética de Columnas",
        pt="Aritmética de Colunas",
        de="Spalten-Arithmetik",
        zh="列算术运算",
    )
    IMAGE_PREVIEW = "column_arithmetic.png"

    metadata = {
        "allowed_types": [Float, Integer],
        "allowed_dtypes": [],
    }

    def __init__(
        self,
        column_a: str,
        operation: str,
        operand_b_mode: str = "column",
        column_b: Union[str, None] = None,
        constant: Union[float, None] = None,
        output_column_name: Union[str, None] = None,
    ):
        """Initialise the converter with the operands and the operation to apply.

        Parameters
        ----------
        column_a : str
            Name of the first operand column. Must be non-empty.
        operation : str
            One of ``"add"``, ``"subtract"``, ``"multiply"``, ``"divide"``.
        operand_b_mode : str, optional
            Either ``"column"`` (default), to use ``column_b`` as the second
            operand, or ``"constant"``, to use ``constant`` instead.
        column_b : str, optional
            Name of the second operand column. Required (non-empty) when
            ``operand_b_mode`` is ``"column"``. May be equal to ``column_a``.
        constant : float, optional
            Fixed number used as the second operand. Required when
            ``operand_b_mode`` is ``"constant"``.
        output_column_name : str, optional
            Name of the resulting column. If ``None`` or not a string, a name
            is generated from the operands and the operation.

        Raises
        ------
        ValueError
            If ``column_a`` is empty, if ``operation`` or ``operand_b_mode``
            is not one of the supported values, or if the operand required by
            ``operand_b_mode`` (``column_b`` or ``constant``) is missing.
        """
        super().__init__()
        if not isinstance(column_a, str) or not column_a:
            raise ValueError("'column_a' must be a non-empty string.")
        if operation not in OPERATIONS:
            raise ValueError(
                f"'operation' must be one of {OPERATIONS}, got '{operation}'."
            )
        if operand_b_mode not in OPERAND_B_MODES:
            raise ValueError(
                f"'operand_b_mode' must be one of {OPERAND_B_MODES}, "
                f"got '{operand_b_mode}'."
            )
        if operand_b_mode == "column" and (
            not isinstance(column_b, str) or not column_b
        ):
            raise ValueError(
                "'column_b' must be a non-empty string when 'operand_b_mode' "
                "is 'column'."
            )
        if operand_b_mode == "constant" and (
            not isinstance(constant, (int, float)) or isinstance(constant, bool)
        ):
            raise ValueError(
                "'constant' must be a number when 'operand_b_mode' is 'constant'."
            )

        self.column_a = column_a
        self.operation = operation
        self.operand_b_mode = operand_b_mode
        self.column_b = column_b if operand_b_mode == "column" else None
        self.constant = float(constant) if operand_b_mode == "constant" else None
        self.output_column_name = (
            output_column_name if isinstance(output_column_name, str) else None
        )
        self._result_column_name: Union[str, None] = None
        self._output_is_integer: bool = False

    @staticmethod
    def _format_constant(value: float) -> str:
        """Render a constant for use in an auto-generated column name."""
        return str(int(value)) if value == int(value) else str(value)

    def fit(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> "ColumnArithmetic":
        """Validate that the operand column(s) are present and numeric.

        Parameters
        ----------
        x : DashAIDataset
            The scoped dataset expected to contain ``column_a`` (and
            ``column_b`` when ``operand_b_mode`` is ``"column"``).
        y : DashAIDataset, optional
            Ignored. Defaults to None.

        Returns
        -------
        ColumnArithmetic
            The fitted converter instance (self).

        Raises
        ------
        ValueError
            If an operand column is missing from ``x`` or is not of a
            numeric (Float or Integer) type.
        """
        operand_columns = (
            (self.column_a, self.column_b)
            if self.operand_b_mode == "column"
            else (self.column_a,)
        )
        for col in operand_columns:
            if col not in x.column_names:
                raise ValueError(
                    f"Column '{col}' was not found in the converter's scope. "
                    "Make sure it is included in the selected columns."
                )
            if col in x.types and not isinstance(x.types[col], (Float, Integer)):
                raise ValueError(
                    f"Column '{col}' must be numeric (Float or Integer) to be "
                    "used in ColumnArithmetic."
                )

        if self.operand_b_mode == "column":
            operand_b_label = self.column_b
            operand_b_is_integer = isinstance(x.types.get(self.column_b), Integer)
        else:
            operand_b_label = self._format_constant(self.constant)
            operand_b_is_integer = self.constant == int(self.constant)

        self._result_column_name = self.output_column_name or (
            f"{self.column_a}_{self.operation}_{operand_b_label}"
        )
        self._output_is_integer = (
            self.operation != "divide"
            and isinstance(x.types.get(self.column_a), Integer)
            and operand_b_is_integer
        )
        return self

    def _get_operand_b(self, x_pandas, dtype: str):
        """Return the second operand as an array aligned with ``x_pandas``.

        Either the values of ``column_b``, or ``constant`` broadcast to the
        same length, depending on ``operand_b_mode``.
        """
        import numpy as np

        if self.operand_b_mode == "column":
            return x_pandas[self.column_b].to_numpy(dtype=dtype)
        return np.full(len(x_pandas), self.constant, dtype=dtype)

    def transform(
        self, x: "DashAIDataset", y: Union["DashAIDataset", None] = None
    ) -> "DashAIDataset":
        """Compute the arithmetic result and append it as a new column.

        Parameters
        ----------
        x : DashAIDataset
            The dataset containing ``column_a`` (and ``column_b`` when
            ``operand_b_mode`` is ``"column"``).
        y : DashAIDataset, optional
            Ignored. Defaults to None.

        Returns
        -------
        DashAIDataset
            The original dataset with the arithmetic result appended as a
            new column, typed ``Integer`` or ``Float`` depending on the
            operands and the operation (see class docstring).
        """
        import numpy as np
        import pyarrow as pa

        from DashAI.back.dataloaders.classes.dashai_dataset import modify_table

        x_pandas = x.to_pandas()

        if self._output_is_integer:
            a = x_pandas[self.column_a].to_numpy(dtype="int64")
            b = self._get_operand_b(x_pandas, "int64")

            if self.operation == "add":
                result = a + b
            elif self.operation == "subtract":
                result = a - b
            else:  # multiply
                result = a * b

            arrow_type = pa.int64()
        else:
            a = x_pandas[self.column_a].to_numpy(dtype="float64")
            b = self._get_operand_b(x_pandas, "float64")

            with np.errstate(divide="ignore", invalid="ignore"):
                if self.operation == "add":
                    result = a + b
                elif self.operation == "subtract":
                    result = a - b
                elif self.operation == "multiply":
                    result = a * b
                else:  # divide
                    result = np.where(b != 0, a / b, np.nan)

            arrow_type = pa.float64()

        new_types = dict(x.types)
        new_types[self._result_column_name] = self.get_output_type()

        return modify_table(
            x,
            {self._result_column_name: pa.array(result, type=arrow_type)},
            types=new_types,
        )

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Return the output type for the arithmetic result.

        Determined during ``fit``: ``Integer`` when both operands are
        ``Integer`` (a whole-number ``constant`` counts as ``Integer``) and
        the operation isn't ``divide``, ``Float`` otherwise.

        Parameters
        ----------
        column_name : str, optional
            Not used; the result column always has the same type.
            Defaults to None.

        Returns
        -------
        DashAIDataType
            An ``Integer`` type backed by ``pyarrow.int64()``, or a
            ``Float`` type backed by ``pyarrow.float64()``.
        """
        import pyarrow as pa

        if self._output_is_integer:
            return Integer(arrow_type=pa.int64())
        return Float(arrow_type=pa.float64())
