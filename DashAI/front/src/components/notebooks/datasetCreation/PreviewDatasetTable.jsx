import { useMemo, useState } from "react";
import {
  Typography,
  Select,
  MenuItem,
  Box,
  TextField,
  Tooltip,
  Chip,
  Menu,
} from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { TypeChangeValidator } from "./TypeChangeValidator";
import InferenceReasonPopover from "../dataset/InferenceReasonPopover";
import { useTranslation } from "react-i18next";
import { useTableLocalization } from "../../../utils/useTableLocalization";
import { useSnackbar } from "notistack";

const TYPE_TO_DEFAULT_DTYPE = {
  Integer: "int64",
  Float: "float64",
  Text: "string",
  Categorical: "string",
  // Date: "date32",
  // Time: "time32(s)",
  // Timestamp: "timestamp(us)",
  // Duration: "duration(us)",
  Decimal: "decimal128(8, 0)",
  Binary: "binary",
  Image: "string",
  // Boolean: "bool",  // Boolean is always Categorical
};

const ENCODER_OPTIONS = ["one_hot", "label"];

/**
 * Table component to display dataset preview with inferred types in column headers.
 *
 * @param {Array} rows - Array of row objects to display
 * @param {Object} columnTypes - Object mapping column names to their inferred types
 *                                (e.g., { columnName: { type: "Categorical", dtype: "string", encoder: "one_hot" } })
 * @param {File} file - The uploaded file (needed for validation)
 * @param {Object} params - Dataloader parameters (needed for validation)
 * @param {Function} onTypeChange - Callback when types are successfully changed
 * @param {Function} onColumnRename - Callback when a column is renamed (oldName, newName) => void
 * @param {Function} onEncoderChange - Callback when encoder changes (columnName, encoder) => void
 */
export default function PreviewDatasetTable({
  rows,
  columnTypes,
  file,
  params,
  onTypeChange,
  onColumnRename,
  onEncoderChange,
}) {
  const { t } = useTranslation(["common"]);
  const localization = useTableLocalization();
  const { enqueueSnackbar } = useSnackbar();
  const [showValidator, setShowValidator] = useState(false);
  const [pendingChanges, setPendingChanges] = useState({});
  const [editingColumn, setEditingColumn] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [columnNames, setColumnNames] = useState({});
  const [encoderAnchor, setEncoderAnchor] = useState(null);
  const [encoderAnchorColumn, setEncoderAnchorColumn] = useState(null);

  const encoderLabel = (enc) => {
    if (enc === "one_hot") return t("common:encoderOneHot");
    if (enc === "label") return t("common:encoderLabel");
    return enc;
  };

  const handleEncoderClick = (e, columnName) => {
    e.stopPropagation();
    setEncoderAnchor(e.currentTarget);
    setEncoderAnchorColumn(columnName);
  };

  const handleEncoderClose = () => {
    setEncoderAnchor(null);
    setEncoderAnchorColumn(null);
  };

  const handleEncoderSelect = (newEncoder) => {
    if (encoderAnchorColumn && onEncoderChange) {
      onEncoderChange(encoderAnchorColumn, newEncoder);
    }
    handleEncoderClose();
  };

  const handleTypeChangeRequest = (columnName, newType) => {
    const currentType = columnTypes[columnName]?.type;

    if (currentType === newType) {
      return;
    }

    const currentDtype = columnTypes[columnName]?.dtype;
    // For Categorical, preserve the column's actual dtype so label encoding
    // uses the correct numeric type rather than defaulting to string.
    const newDtype =
      newType === "Categorical" && currentDtype
        ? currentDtype
        : TYPE_TO_DEFAULT_DTYPE[newType] || "string";

    setPendingChanges({
      [columnName]: {
        current_type: currentType,
        new_type: newType,
        new_dtype: newDtype,
      },
    });

    setShowValidator(true);
  };

  const handleConfirmChanges = (changes) => {
    if (onTypeChange) {
      onTypeChange(changes);
    }
    setShowValidator(false);
    setPendingChanges({});
  };

  const handleCancelChanges = () => {
    setShowValidator(false);
    setPendingChanges({});
  };

  const handleStartEdit = (columnName) => {
    setEditingColumn(columnName);
    setEditValue(columnNames[columnName] || columnName);
  };

  const handleCancelEdit = () => {
    setEditingColumn(null);
    setEditValue("");
  };

  const handleConfirmEdit = (oldName) => {
    const newName = editValue.trim();

    if (!newName) {
      enqueueSnackbar(t("common:columnNameCannotBeEmpty"), {
        variant: "warning",
      });
      handleCancelEdit();
      return;
    }

    const columnNameRegex = /^[a-zA-Z0-9_]+$/;
    if (!columnNameRegex.test(newName)) {
      enqueueSnackbar(t("common:columnNameInvalidCharacters"), {
        variant: "warning",
      });
      handleCancelEdit();
      return;
    }

    if (newName === oldName || newName === (columnNames[oldName] || oldName)) {
      handleCancelEdit();
      return;
    }

    const allColumnNames = Object.keys(columnTypes).map(
      (col) => columnNames[col] || col,
    );

    if (allColumnNames.includes(newName)) {
      enqueueSnackbar(t("common:columnNameAlreadyExists"), {
        variant: "warning",
      });
      handleCancelEdit();
      return;
    }

    setColumnNames((prev) => ({
      ...prev,
      [oldName]: newName,
    }));

    if (onColumnRename) {
      onColumnRename(oldName, newName);
    }

    handleCancelEdit();
  };

  const handleKeyDown = (e, columnName) => {
    if (e.key === "Enter") {
      handleConfirmEdit(columnName);
    } else if (e.key === "Escape") {
      handleCancelEdit();
    }
  };

  const columns = useMemo(() => {
    if (!rows || rows.length === 0) return [];

    const firstRow = rows[0];
    return Object.keys(firstRow).map((field) => {
      const columnType = columnTypes[field];
      const displayName = columnNames[field] || field;
      const isImage =
        columnType?.type === "Image" ||
        (typeof firstRow[field] === "string" &&
          firstRow[field].startsWith("data:image"));

      return {
        accessorKey: field,
        header: displayName,
        minSize: 150,
        grow: 1,
        enableSorting: false,
        enableColumnActions: false,
        Cell: ({ cell }) => {
          const val = cell.getValue();
          if (typeof val === "string" && val.startsWith("data:image")) {
            return (
              <img
                src={val}
                alt="img"
                style={{
                  maxHeight: 48,
                  maxWidth: 48,
                  objectFit: "contain",
                }}
              />
            );
          }
          if (typeof val === "boolean") return String(val);
          return val;
        },
        ...(isImage && { size: 80 }),
        Header: () => (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              width: "100%",
              gap: 1,
            }}
          >
            {editingColumn === field ? (
              <TextField
                autoFocus
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => handleKeyDown(e, field)}
                onBlur={() => handleConfirmEdit(field)}
                size="small"
                sx={{
                  width: "100%",
                  "& .MuiInputBase-input": {
                    fontSize: "0.875rem",
                    paddingY: 1,
                  },
                }}
              />
            ) : (
              <Tooltip title={t("common:renameColumn")} arrow>
                <Typography
                  variant="body1"
                  onDoubleClick={() => handleStartEdit(field)}
                  sx={{
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.2s",
                    "&:hover": {
                      color: "primary.main",
                      textDecoration: "underline",
                    },
                  }}
                >
                  {displayName}
                </Typography>
              </Tooltip>
            )}

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Select
                value={columnType?.type || "Text"}
                onChange={(e) => handleTypeChangeRequest(field, e.target.value)}
                size="small"
                disabled={editingColumn === field}
                sx={{
                  fontSize: "0.75rem",
                  minWidth: 120,
                  "& .MuiSelect-select": {
                    paddingY: 1,
                    paddingX: 1,
                  },
                }}
              >
                <MenuItem value="Integer">Integer</MenuItem>
                <MenuItem value="Float">Float</MenuItem>
                <MenuItem value="Text">Text</MenuItem>
                <MenuItem value="Categorical">Categorical</MenuItem>
                <MenuItem value="Image">Image</MenuItem>
              </Select>

              <InferenceReasonPopover
                columnName={displayName}
                reason={columnType?.inference_reason}
              />
            </Box>

            {columnType?.type === "Categorical" && columnType?.encoder && (
              <Tooltip title={t("common:changeEncoder")} arrow>
                <span style={{ display: "inline-flex" }}>
                  <Chip
                    label={encoderLabel(columnType.encoder)}
                    size="small"
                    onClick={(e) => handleEncoderClick(e, field)}
                    aria-label={t("common:encoder")}
                    sx={{
                      fontSize: "0.65rem",
                      height: "18px",
                      cursor: "pointer",
                    }}
                  />
                </span>
              </Tooltip>
            )}
          </Box>
        ),
      };
    });
  }, [
    rows,
    columnTypes,
    columnNames,
    editingColumn,
    editValue,
    encoderAnchorColumn,
    t,
  ]);

  const table = useMaterialReactTable({
    columns,
    data: rows ?? [],
    muiTableBodyCellProps: { sx: { whiteSpace: "pre" } },
    localization,
    initialState: {
      density: "compact",
      pagination: { pageSize: 5, pageIndex: 0 },
    },
    muiTablePaperProps: { elevation: 0 },
    paginationDisplayMode: "pages",
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enableHiding: false,
    enableTopToolbar: false,
  });

  return (
    <>
      <MaterialReactTable table={table} />

      <Menu
        anchorEl={encoderAnchor}
        open={Boolean(encoderAnchor)}
        onClose={handleEncoderClose}
      >
        {ENCODER_OPTIONS.map((enc) => (
          <MenuItem
            key={enc}
            selected={enc === columnTypes[encoderAnchorColumn]?.encoder}
            onClick={() => handleEncoderSelect(enc)}
            sx={{ fontSize: "0.85rem" }}
          >
            {encoderLabel(enc)}
          </MenuItem>
        ))}
      </Menu>

      <TypeChangeValidator
        open={showValidator}
        onClose={handleCancelChanges}
        onConfirm={handleConfirmChanges}
        file={file}
        typeChanges={pendingChanges}
        params={params}
      />
    </>
  );
}
