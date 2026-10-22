from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Final,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from starlette.datastructures import UploadFile

from DashAI.back.tasks.column_roles import ColumnRole, IOColumns, type_name
from DashAI.back.tasks.utils import get_bytes_with_type_filetype

if TYPE_CHECKING:
    from datasets import DatasetDict

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseTask:
    """Base class for DashAI compatible tasks."""

    TYPE: Final[str] = "Task"
    REQUIRES_TARGET: bool = True

    PREDICTS_FORWARD_ONLY: bool = False

    # The roles this task's columns can play. Left as None, the roles come
    # from the x/y short form of ``metadata`` (see ``_role_delegate``).
    COLUMN_ROLES: Optional[Tuple[ColumnRole, ...]] = None

    @property
    def schema(self) -> Dict[str, Any]:
        """Return optional task-specific configuration schema.

        Most modeling tasks do not need an additional schema beyond their
        metadata and compatible components, so the default is an empty mapping.
        Concrete tasks can override this property when they require extra
        task-level parameters.

        Returns
        -------
        Dict[str, Any]
            Task-specific schema, or an empty dictionary when not applicable.
        """
        return {}

    @classmethod
    def _role_delegate(cls) -> Optional[type]:
        """Decide, in this one place, who declares and translates the roles.

        - A task that declares ``COLUMN_ROLES`` wins: the roles are its own,
          the flat metadata is not read for them, and the task translates
          them itself (``io_roles``, ``io_columns`` and ``roles_from_io``).
        - A task that declares only the x/y short form (``inputs_types``
          beside ``outputs_types`` and their cardinalities) is handed to the
          x/y family, which reads that form as roles. This is how every
          built-in task, every test task and every plugin written before
          roles existed keep working unchanged.
        - A task that declares neither cannot be used: there is no way to
          know what its columns are for.

        Returns
        -------
        type or None
            The class whose methods declare and translate the roles, or
            ``None`` when the task does it itself.

        Raises
        ------
        NotImplementedError
            If the task declares neither roles nor the x/y short form.
        """
        if cls.COLUMN_ROLES is not None:
            return None
        metadata = getattr(cls, "metadata", None) or {}
        if "inputs_types" in metadata and "outputs_types" in metadata:
            from DashAI.back.tasks.xy_roles import XYRoles

            return XYRoles
        raise NotImplementedError(
            f"{cls.__name__} declares no column roles. Declare COLUMN_ROLES "
            "(and override io_roles, io_columns and roles_from_io), or the "
            "short form of a task that maps inputs to outputs: inputs_types, "
            "inputs_cardinality, outputs_types and outputs_cardinality in "
            "its metadata."
        )

    @classmethod
    def _own_translation_missing(cls) -> NotImplementedError:
        """The error for a task with its own roles but no translation."""
        return NotImplementedError(
            f"{cls.__name__} declares its own COLUMN_ROLES, so it has to say "
            "how they feed a model: override io_roles, io_columns and "
            "roles_from_io."
        )

    @classmethod
    def column_roles(cls) -> Tuple[ColumnRole, ...]:
        """The roles this task's columns can play, in the order it declares.

        Returns
        -------
        tuple of ColumnRole
            The declared roles.
        """
        delegate = cls._role_delegate()
        if delegate is None:
            return tuple(cls.COLUMN_ROLES)
        return delegate.column_roles(cls)

    @classmethod
    def io_roles(cls) -> Dict[str, List[str]]:
        """Which roles feed a model's inputs and which its outputs.

        Returns
        -------
        dict
            ``{"inputs": [role names], "outputs": [role names]}``.
        """
        delegate = cls._role_delegate()
        if delegate is None:
            raise cls._own_translation_missing()
        return delegate.io_roles(cls)

    def io_columns(self, roles: Mapping[str, Sequence]) -> IOColumns:
        """Translate a session's roles into a model's inputs and outputs.

        Parameters
        ----------
        roles : mapping
            Role name to the role's columns, as names or as column refs.

        Returns
        -------
        IOColumns
            The entries that feed the model as ``x`` and as ``y``.
        """
        delegate = self._role_delegate()
        if delegate is None:
            raise self._own_translation_missing()
        return delegate.io_columns(type(self), roles)

    def roles_from_io(
        self, input_columns: Sequence, output_columns: Sequence
    ) -> Dict[str, list]:
        """Translate a model's inputs and outputs back into roles.

        The units still hand tasks the columns as inputs and outputs, so
        ``validate_dataset_for_task`` reads them as roles through this.

        Parameters
        ----------
        input_columns, output_columns : sequence
            The columns fed to the model as ``x`` and as ``y``.

        Returns
        -------
        dict
            Role name to the role's columns.
        """
        delegate = self._role_delegate()
        if delegate is None:
            raise self._own_translation_missing()
        return delegate.roles_from_io(type(self), input_columns, output_columns)

    @staticmethod
    def _total_cardinality(roles: List[ColumnRole]) -> Any:
        """State a whole side's cardinality the way the flat contract did.

        Kept so every consumer of the flat metadata, the column picker among
        them, reads the same value it always did.

        Parameters
        ----------
        roles : list of ColumnRole
            The roles of one side.

        Returns
        -------
        int or str
            The exact total when every role is exact, otherwise ``"n"``.
        """
        if all(role.min == role.max for role in roles):
            return sum(role.min for role in roles)
        return "n"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Return serialisable metadata for the current task.

        ``"column_roles"`` lists the roles and ``"io_roles"`` which of them
        feed a model's inputs and outputs. ``"inputs_types"`` and the three
        keys beside it are the flat view the remaining consumers read,
        computed from the roles of each side.

        Type classes become their string names throughout so the result can be
        JSON-serialised by the DashAI frontend.

        Parameters
        ----------
        cls : type
            The task class (injected automatically by Python for classmethods).

        Returns
        -------
        Dict[str, Any]
            Dictionary with keys ``"inputs_types"``, ``"outputs_types"``,
            ``"inputs_cardinality"``, ``"outputs_cardinality"``,
            ``"column_roles"``, ``"io_roles"`` and ``"requires_target"``.
        """
        roles = cls.column_roles()
        sides = cls.io_roles()
        by_name = {role.name: role for role in roles}
        parsed_metadata: dict = {}

        for side in ("inputs", "outputs"):
            side_roles = [by_name[name] for name in sides[side] if name in by_name]

            names: List[str] = []
            for role in side_roles:
                for dashai_type in role.types:
                    name = type_name(dashai_type)
                    if name not in names:
                        names.append(name)

            parsed_metadata[f"{side}_types"] = names
            parsed_metadata[f"{side}_cardinality"] = cls._total_cardinality(side_roles)

        parsed_metadata["column_roles"] = [role.to_metadata() for role in roles]
        parsed_metadata["io_roles"] = sides
        parsed_metadata["requires_target"] = cls.REQUIRES_TARGET

        return parsed_metadata

    @staticmethod
    def _role_noun(role_name: str, sides: Dict[str, List[str]]) -> str:
        """What an error message calls a role's columns.

        Columns that feed a model are its input or output columns; any other
        role is named after itself.
        """
        if role_name in sides["inputs"]:
            return "input"
        if role_name in sides["outputs"]:
            return "output"
        return role_name

    def check_role_names(self, roles: Mapping[str, Any]) -> None:
        """Refuse a role this task does not declare.

        Raises
        ------
        ValueError
            Naming the first undeclared role and the task's roles.
        """
        names = [role.name for role in self.column_roles()]
        for name in roles:
            if name not in names:
                raise ValueError(
                    f"{type(self).__name__} has no column role {name!r}. Its "
                    f"roles are: {', '.join(names)}."
                )

    def _declared_role(self, role_name: str) -> ColumnRole:
        for role in self.column_roles():
            if role.name == role_name:
                return role
        raise ValueError(f"{type(self).__name__} has no column role {role_name!r}.")

    def validate_role(
        self, role_name: str, columns: Sequence[str], types: Mapping[str, Any]
    ) -> None:
        """Check one role's columns against its types and cardinality.

        Parameters
        ----------
        role_name : str
            A declared role.
        columns : sequence of str
            The names of the role's columns.
        types : mapping
            The dataset's column types, keyed by column name.

        Raises
        ------
        TypeError
            If a column's type is not one the role accepts.
        ValueError
            If the role gets a number of columns outside its cardinality.
        """
        role = self._declared_role(role_name)
        noun = self._role_noun(role.name, self.io_roles())
        for column in columns:
            column_type = types[column]
            if not isinstance(column_type, role.types):
                raise TypeError(
                    f"{column_type} is not an allowed type for {noun} columns."
                )
        if not role.admits(len(columns)):
            raise ValueError(
                f"{noun.capitalize()} cardinality ({len(columns)}) does not "
                f"match task cardinality ({role.cardinality_text()})"
            )

    def validate_estimated_role(
        self, role_name: str, columns: Sequence[Tuple[Optional[str], Optional[int]]]
    ) -> None:
        """Check one role against the columns a preprocessing chain will give it.

        Before the chain is fitted, its estimated structure only names the
        type of each output and may not know how many columns a block holds.

        Parameters
        ----------
        role_name : str
            A declared role.
        columns : sequence of (type name, count)
            One entry per estimated output: the name of its type, or None when
            unknown, and how many columns it holds, or None when unknown. An
            unknown count is taken as at least one, and only the role's
            minimum is checked then.

        Raises
        ------
        TypeError
            If an output's type is not one the role accepts.
        ValueError
            If the role gets a number of columns outside its cardinality.
        """
        role = self._declared_role(role_name)
        noun = self._role_noun(role.name, self.io_roles())
        for column_type, _ in columns:
            if not role.accepts_type_name(column_type):
                raise TypeError(
                    f"{column_type} is not an allowed type for {noun} columns."
                )
        known = sum(count for _, count in columns if count is not None)
        unknown = sum(1 for _, count in columns if count is None)
        fits = known + unknown >= role.min if unknown else role.admits(known)
        if not fits:
            raise ValueError(
                f"{noun.capitalize()} cardinality ({known + unknown}) does not "
                f"match task cardinality ({role.cardinality_text()})"
            )

    def validate_roles(
        self, roles: Mapping[str, Sequence[str]], types: Mapping[str, Any]
    ) -> None:
        """Check a session's columns, role by role, against the declaration.

        Roles are checked in the order the task declares them. A role the
        mapping leaves out counts as given no columns.

        Parameters
        ----------
        roles : mapping
            Role name to the names of the role's columns.
        types : mapping
            The dataset's column types, keyed by column name.

        Raises
        ------
        ValueError
            If a role is not declared, or gets a number of columns outside its
            cardinality.
        TypeError
            If a column's type is not one its role accepts.
        """
        self.check_role_names(roles)
        for role in self.column_roles():
            self.validate_role(role.name, list(roles.get(role.name) or []), types)

    def validate_dataset_for_task(
        self,
        dataset: "DashAIDataset",
        dataset_name: str,
        input_columns: List[str],
        output_columns: List[str] | None,
    ) -> None:
        """Validate a dataset for the current task.

        The columns arrive as a model's inputs and outputs, the way the units
        hand them over, and are checked as the roles they came from.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to be validated
        dataset_name : str
            Dataset name
        input_columns : list of str
            Names of the columns selected as inputs.
        output_columns : list of str
            Names of the columns selected as outputs.
        """
        roles = self.roles_from_io(input_columns, output_columns or [])
        self.validate_roles(roles, dataset._types)

    def prepare_for_task(
        self,
        dataset: Union["DatasetDict", "DashAIDataset"],
        input_columns: List[str],
        output_columns: List[str] | None = None,
    ) -> "DashAIDataset":
        """Prepare and validate a dataset for this task.

        Ensures the dataset is a ``DashAIDataset`` instance, then validates
        that the selected input and output columns match the types and
        cardinality declared in :attr:`metadata`.

        Parameters
        ----------
        dataset : DatasetDict or DashAIDataset
            The dataset to prepare. If a ``DatasetDict`` is supplied it is
            converted to ``DashAIDataset`` automatically.
        input_columns : list of str
            Names of columns to use as model inputs.
        output_columns : list of str, optional
            Names of columns to use as model outputs/targets. Tasks without
            targets, such as clustering, can omit this argument.

        Returns
        -------
        DashAIDataset
            The validated dataset, ready to be passed to a model.

        Raises
        ------
        TypeError
            If any input or output column has a type not allowed by this task.
        ValueError
            If the number of input or output columns violates the task's
            cardinality constraints.
        """
        from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset

        dashai_dataset = to_dashai_dataset(dataset)
        output_columns = output_columns or []
        self.validate_dataset_for_task(
            dashai_dataset,
            dataset_name=getattr(dashai_dataset, "name", "dataset"),
            input_columns=input_columns,
            output_columns=output_columns,
        )
        return dashai_dataset

    def _validate_and_normalize_value(
        self,
        value: Any,
        column_spec: Dict[str, Any],
        column_name: str,
        row_idx: int,
    ) -> Any:
        """Validate and normalize a value against expected column specification.

        Parameters
        ----------
        value : Any
            Value to validate
        column_spec : Dict[str, Any]
            Column specification with 'type', 'dtype', 'categories', etc.
        column_name : str
            Name of the column being validated
        row_idx : int
            Index of the row being validated

        Returns
        -------
        Any
            Normalized value, or None for a missing cell (None or NaN).

        Raises
        ------
        ValueError
            If categorical value is not in allowed categories
        TypeError
            If value doesn't match expected type
        """
        import numpy as np

        # A missing cell is not a wrong type: a session may impute it, and a
        # model that cannot handle it is reported by the prediction step,
        # which names the rows and columns.
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None

        col_type = column_spec.get("type")
        dtype = column_spec.get("dtype")

        if col_type == "Categorical":
            categories = column_spec.get("categories", [])

            if dtype and dtype.startswith("int"):
                if isinstance(value, bool):
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Boolean cannot be converted to integer categorical"
                    )
                try:
                    normalized_value = int(float(value))
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Cannot convert '{value}' to integer categorical"
                    ) from e

            elif dtype and dtype.startswith("float"):
                if isinstance(value, bool):
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Boolean cannot be converted to float categorical"
                    )
                try:
                    normalized_value = float(value)
                except (TypeError, ValueError) as e:
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Cannot convert '{value}' to float categorical"
                    ) from e

            elif dtype == "bool":
                if isinstance(value, bool):
                    normalized_value = value
                elif isinstance(value, str):
                    if value.lower() in ("true", "1", "yes"):
                        normalized_value = True
                    elif value.lower() in ("false", "0", "no"):
                        normalized_value = False
                    else:
                        raise ValueError(
                            f"Row {row_idx}, column '{column_name}': "
                            f"Cannot convert '{value}' to boolean"
                        )
                else:
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Expected boolean categorical, got {type(value).__name__}"
                    )

            else:
                # String categorical
                normalized_value = str(value)

            if str(normalized_value) not in [str(cat) for cat in categories]:
                raise ValueError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Value '{value}' is not valid. "
                    f"Allowed: {categories}"
                )

            return normalized_value

        if col_type == "Float":
            if isinstance(value, bool):
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Boolean cannot be converted to Float"
                )
            try:
                return float(value)
            except (TypeError, ValueError) as e:
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Cannot convert '{value}' to Float"
                ) from e

        if col_type == "Integer":
            if isinstance(value, bool):
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Boolean cannot be converted to Integer"
                )
            try:
                int_val = int(value)
                if isinstance(value, float) and not np.isclose(value, int_val):
                    raise TypeError(
                        f"Row {row_idx}, column '{column_name}': "
                        f"Float value '{value}' has decimals, cannot convert to Integer"
                    )
                return int_val
            except (TypeError, ValueError) as e:
                raise TypeError(
                    f"Row {row_idx}, column '{column_name}': "
                    f"Cannot convert '{value}' to Integer"
                ) from e

        if col_type == "Text":
            return str(value)

        # Unknown type
        return value

    def process_manual_input(
        self, manual_input: List[dict], dataset_path: str
    ) -> "DashAIDataset":
        """Process manual input data into a DashAIDataset with type validation.

        Parameters
        ----------
        manual_input : List[dict]
            List of dictionaries representing manual input data.
        dataset_path : str
            Path to the training dataset (used to get column specs for validation)

        Returns
        -------
        DashAIDataset
            Processed DashAIDataset from manual input.

        Raises
        ------
        ValueError
            If input cardinality doesn't match or categorical value is invalid
        TypeError
            If input types don't match expected types
        """
        from pandas import DataFrame

        from DashAI.back.dataloaders.classes.dashai_dataset import (
            get_columns_spec,
            to_dashai_dataset,
            transform_dataset_with_schema,
        )

        columns_spec = get_columns_spec(dataset_path)
        inputs_cardinality = self.get_metadata()["inputs_cardinality"]

        if inputs_cardinality != "n" and len(manual_input[0]) != inputs_cardinality:
            raise ValueError(
                f"Input cardinality ({len(manual_input[0])}) does not "
                f"match task cardinality ({inputs_cardinality})"
            )

        mapped_inputs = []
        for row_idx, input_dict in enumerate(manual_input):
            row = {}
            for col_name, value in input_dict.items():
                column_spec = columns_spec.get(col_name)
                if not column_spec:
                    raise ValueError(
                        f"Column '{col_name}' not found in training dataset"
                    )

                # File case (image, audio, video, etc.)
                if isinstance(value, UploadFile):
                    file_bytes = value.file.read()
                    data, detected_type = get_bytes_with_type_filetype(file_bytes)
                    expected_type = column_spec.get("type", "")
                    if detected_type.lower() != expected_type.lower():
                        raise TypeError(
                            f"Row {row_idx}, column '{col_name}': "
                            f"File type '{detected_type}' doesn't match "
                            f"expected type '{expected_type}'"
                        )
                    if detected_type == "image":
                        # Store in the same struct format used by the image dataloader
                        # so DashAIDataset.__getitem__ can wrap it in DashAIImage.
                        fname = getattr(value, "filename", None) or ""
                        row[col_name] = {"bytes": data, "path": fname}
                    else:
                        row[col_name] = data

                # File saved to disk by job queue
                elif isinstance(value, dict) and "__image_file__" in value:
                    file_path_on_disk = value["__image_file__"]
                    with open(file_path_on_disk, "rb") as f:
                        file_bytes = f.read()
                    data, detected_type = get_bytes_with_type_filetype(file_bytes)
                    expected_type = column_spec.get("type", "")
                    if detected_type.lower() != expected_type.lower():
                        raise TypeError(
                            f"Row {row_idx}, column '{col_name}': "
                            f"File type '{detected_type}' doesn't match "
                            f"expected type '{expected_type}'"
                        )
                    if detected_type == "image":
                        import os

                        row[col_name] = {
                            "bytes": data,
                            "path": os.path.basename(file_path_on_disk),
                        }
                    else:
                        row[col_name] = data

                # Primitive value
                else:
                    normalized_value = self._validate_and_normalize_value(
                        value, column_spec, col_name, row_idx
                    )
                    row[col_name] = normalized_value

            mapped_inputs.append(row)

        # Convert to DataFrame first
        mapped_inputs_df = DataFrame(mapped_inputs)

        # Convert to DashAIDataset and apply schema transformation
        # This ensures categorical encoding is applied
        dashai_dataset = to_dashai_dataset(mapped_inputs_df)
        dashai_dataset = transform_dataset_with_schema(dashai_dataset, columns_spec)

        return dashai_dataset
