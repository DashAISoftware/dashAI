import { useState, useEffect, useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import { Box, Typography, Chip, Stack } from "@mui/material";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { getDatasetTypesByFilePath } from "../../api/datasets";
import { Trans, useTranslation } from "react-i18next";

/**
 * Generic column selection component that can be reused across the application
 *
 * Features:
 * - Configurable cardinality constraints (min, max, exact)
 * - Data type filtering (allowed/restricted)
 * - Automatic selection based on cardinality rules
 * - Visual feedback for invalid/disabled columns
 * - Customizable grid columns and styling
 * - Validation callbacks for real-time feedback
 *
 * Usage:
 * - Any component requiring column selection with constraints
 *
 * @param {Object} props
 * @param {Array} props.file_path - String path to the dataset file
 * @param {Object} props.inputCardinality - Cardinality requirements {min, max, exact} (optional)
 * @param {Array} props.allowedDtypes - Array of allowed data types (optional)
 * @param {Array} props.restrictedDtypes - Array of restricted data types (optional)
 * @param {Function} props.onSelectionChange - Callback when selection changes (selectedColumns) (optional)
 * @param {Function} props.onValidationChange - Callback when validation status changes (isValid) (optional)

 */
function ColumnSelector({
  file_path,
  inputCardinality = {},
  allowedDtypes = [],
  restrictedDtypes = [],
  onSelectionChange = () => {},
  onValidationChange = () => {},
}) {
  const [rows, setRows] = useState([]);
  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [datasetColumns, setDatasetColumns] = useState([]);
  const { t, i18n } = useTranslation(["datasets", "common"]);
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  const toMRT = (ids) =>
    Object.fromEntries(ids.map((id) => [String(id), true]));
  const fromMRT = (sel) =>
    Object.keys(sel)
      .filter((k) => sel[k])
      .map(Number);

  const columns = useMemo(
    () => [
      {
        accessorKey: "id",
        header: t("common:index"),
        size: 60,
      },
      {
        accessorKey: "columnName",
        header: t("datasets:label.columnName"),
        flex: 1,
      },
      {
        accessorKey: "valueType",
        header: t("datasets:label.valueType"),
        flex: 0.5,
      },
      {
        accessorKey: "dataType",
        header: t("datasets:label.dataType"),
        flex: 0.5,
      },
      {
        accessorKey: "order",
        header: t("datasets:label.selectedOrder"),
        flex: 0.5,
      },
    ],
    [t],
  );

  useEffect(() => {
    let isMounted = true;
    const fetchAllData = async () => {
      try {
        const types = await getDatasetTypesByFilePath(file_path);

        if (!isMounted) return;

        const datasetColumns = Object.entries(types).map(
          ([columnName, typeInfo], idx) => ({
            id: idx,
            columnName: columnName,
            valueType: typeInfo.type || t("common:unknown"),
            dataType: typeInfo.dtype || t("common:unknown"),
            order: idx,
          }),
        );

        setDatasetColumns(datasetColumns);
        setRows(datasetColumns);
      } catch (error) {
        console.error("Error fetching dataset info/types:", error);
      }
    };

    fetchAllData();

    return () => {
      isMounted = false;
    };
  }, [file_path]);

  // Validate current selection
  const isValidSelection = useCallback(
    (selection) => {
      if (selection.length === 0) {
        return false;
      }

      if (
        inputCardinality.exact &&
        selection.length !== inputCardinality.exact
      ) {
        return false;
      }

      if (inputCardinality.min && selection.length < inputCardinality.min) {
        return false;
      }

      if (inputCardinality.max && selection.length > inputCardinality.max) {
        return false;
      }

      return true;
    },
    [inputCardinality],
  );
  const getValidColumnIds = useCallback(() => {
    return rows
      .filter((row) => {
        if (allowedDtypes.length > 0 && !allowedDtypes.includes("*")) {
          if (!allowedDtypes.includes(row.dataType)) {
            return false;
          }
        }
        if (restrictedDtypes.length > 0) {
          if (restrictedDtypes.includes(row.dataType)) {
            return false;
          }
        }
        return true;
      })
      .map((row) => row.id);
  }, [rows, allowedDtypes, restrictedDtypes]);

  // Check if row is selectable - using useCallback for stability
  const isRowSelectable = useCallback(
    (params) => {
      const validIds = getValidColumnIds();
      const isColumnValid = validIds.includes(params.id);

      if (!isColumnValid) {
        return false;
      }

      const selectedCount = rowSelectionModel.length;
      const isAlreadySelected = rowSelectionModel.includes(params.id);

      // If already selected, always allow deselection
      if (isAlreadySelected) {
        return true;
      }

      // Check exact cardinality constraint
      if (inputCardinality.exact && selectedCount >= inputCardinality.exact) {
        return false;
      }

      // Check max cardinality constraint
      if (inputCardinality.max && selectedCount >= inputCardinality.max) {
        return false;
      }

      return true;
    },
    [getValidColumnIds, rowSelectionModel, inputCardinality],
  );

  // Effect to update selection data and validation whenever rowSelectionModel changes
  useEffect(() => {
    if (rows.length > 0) {
      const selectedColumnsData = rowSelectionModel
        .map((selectedId, index) => {
          const row = rows.find((r) => r.id === selectedId);
          return row
            ? {
                ...row,
                order: index + 1,
              }
            : null;
        })
        .filter(Boolean);

      onSelectionChange(selectedColumnsData);

      const isValid = isValidSelection(rowSelectionModel);
      onValidationChange(isValid);
    }
  }, [rowSelectionModel, rows.length]);

  const handleSelection = (updaterOrValue) => {
    const newMRTSelection =
      typeof updaterOrValue === "function"
        ? updaterOrValue(toMRT(rowSelectionModel))
        : updaterOrValue;
    let selection = fromMRT(newMRTSelection);
    if (inputCardinality.max && selection.length > inputCardinality.max) {
      selection = selection.slice(0, inputCardinality.max);
    }
    const newRows = rows.map((row) => {
      const order = selection.indexOf(row.id) + 1;
      return { ...row, order };
    });

    setRows(newRows);
    setRowSelectionModel(selection);
  };

  const columnSelectorTable = useMaterialReactTable({
    columns,
    data: rows,
    enableRowSelection: (row) => isRowSelectable({ id: row.original.id }),
    onRowSelectionChange: handleSelection,
    state: { rowSelection: toMRT(rowSelectionModel) },
    getRowId: (row) => String(row.id),
    enableGlobalFilter: true,
    enableColumnFilters: false,
    enableSorting: true,
    enablePagination: true,
    muiPaginationProps: { rowsPerPageOptions: [5, 10, 20] },
    initialState: {
      pagination: { pageSize: 5, pageIndex: 0 },
      density: "compact",
    },
    mrtTheme: {
      baseBackgroundColor: theme.palette.ui.panelDark,
    },
    muiTablePaperProps: {
      elevation: 0,
      sx: { border: "1px solid", borderColor: "divider" },
    },
    muiTableBodyRowProps: ({ row }) => ({
      sx: isRowSelectable({ id: row.original.id })
        ? {}
        : { backgroundColor: theme.palette.action.disabledBackground },
    }),
    localization,
  });

  const valid = isValidSelection(rowSelectionModel);

  return (
    <Box>
      {/* Selected count - always shown */}
      <Box
        sx={{
          mb: 2,
          p: 2,
          borderRadius: 2,
          backgroundColor: theme.palette.ui.hover,
          border: `1px solid ${theme.palette.ui.divider}`,
          textAlign: "center",
        }}
      >
        {/* Column requirement info */}
        {Object.keys(inputCardinality).length > 0 && (
          <Typography variant="body1" sx={{ color: "text.secondary", mb: 0.5 }}>
            {t("datasets:label.requiredColumns", {
              exact: inputCardinality.exact,
              min: inputCardinality.min || 0,
              max: inputCardinality.max,
              context: inputCardinality.exact
                ? "exact"
                : inputCardinality.max
                ? "range"
                : "min",
            })}
          </Typography>
        )}

        {/* Selected count */}
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            color: valid ? "success.main" : "error.main",
            letterSpacing: 0.3,
            mb:
              (allowedDtypes?.length > 0 && !allowedDtypes.includes("*")) ||
              restrictedDtypes?.length > 0
                ? 1
                : 0,
          }}
        >
          {t("datasets:label.selectedColumns", {
            count: rowSelectionModel.length,
          })}
        </Typography>

        {/* Allowed data types */}
        {allowedDtypes?.length > 0 && !allowedDtypes.includes("*") && (
          <Typography
            variant="body2"
            sx={{
              color: "text.disabled",
              fontStyle: "italic",
              mt: 1,
            }}
          >
            <Trans i18nKey="datasets:label.allowedDataTypes">
              Allowed data types:
              <Box
                component="span"
                sx={{ color: "secondary.main", fontWeight: 500 }}
              >
                {allowedDtypes.join(", ")}
              </Box>
            </Trans>
          </Typography>
        )}
        {/* Restricted data types */}
        {restrictedDtypes?.length > 0 && (
          <Typography
            variant="body2"
            sx={{
              color: "text.disabled",
              fontStyle: "italic",
              mt: 1,
            }}
          >
            <Trans i18nKey="datasets:label.restrictedDataTypes">
              Restricted data types:
              <Box
                component="span"
                sx={{ color: "secondary.main", fontWeight: 500 }}
              >
                {restrictedDtypes.join(", ")}
              </Box>
            </Trans>
          </Typography>
        )}
      </Box>{" "}
      {/* Data Grid */}
      <MaterialReactTable
        data-tour="column-selector"
        table={columnSelectorTable}
      />
    </Box>
  );
}

ColumnSelector.propTypes = {
  file_path: PropTypes.string.isRequired,
  inputCardinality: PropTypes.shape({
    min: PropTypes.number,
    max: PropTypes.number,
    exact: PropTypes.number,
  }),
  allowedDtypes: PropTypes.array,
  restrictedDtypes: PropTypes.array,
  onSelectionChange: PropTypes.func,
  onValidationChange: PropTypes.func,
};

export default ColumnSelector;
