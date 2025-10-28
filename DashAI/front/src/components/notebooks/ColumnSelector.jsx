import { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import { Box, Typography, Chip, Stack } from "@mui/material";
import { DataGrid, GridToolbarQuickFilter } from "@mui/x-data-grid";
import { getDatasetTypesByFilePath } from "../../api/datasets";

const columns = [
  {
    field: "id",
    headerName: "Index",
  },
  {
    field: "columnName",
    headerName: "Column Name",
    flex: 1,
  },
  {
    field: "valueType",
    headerName: "Value Type",
    flex: 0.5,
  },
  {
    field: "dataType",
    headerName: "Data Type",
    flex: 0.5,
  },
  {
    field: "order",
    headerName: "Selected Order",
    type: "number",
    flex: 0.5,
  },
];

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
            valueType: typeInfo.type || "Unknown",
            dataType: typeInfo.dtype || "Unknown",
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

  const handleSelection = (selection) => {
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

  const valid = isValidSelection(rowSelectionModel);

  return (
    <Box>
      {Object.keys(inputCardinality).length > 0 && (
        <Box
          sx={{
            mb: 2,
            p: 2,
            borderRadius: 2,
            backgroundColor: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.15)",
            textAlign: "center",
          }}
        >
          {/* Column requirement info */}
          <Typography
            variant="body1"
            sx={{ color: "rgba(255, 255, 255, 0.7)", mb: 0.5 }}
          >
            Required columns:
            {inputCardinality.exact
              ? ` exactly ${inputCardinality.exact}`
              : inputCardinality.max
                ? ` between ${inputCardinality.min || 0} and ${
                    inputCardinality.max
                  }`
                : ` at least ${inputCardinality.min || 0}`}
          </Typography>

          {/* Selected count */}
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              color: valid ? "success.main" : "error.main",
              letterSpacing: 0.3,
              mb: allowedDtypes?.length > 0 ? 1 : 0,
            }}
          >
            {`Selected ${rowSelectionModel.length} column${
              rowSelectionModel.length !== 1 ? "s" : ""
            }`}
          </Typography>

          {/* Allowed data types */}
          {allowedDtypes?.length > 0 && !allowedDtypes.includes("*") && (
            <Typography
              variant="body2"
              sx={{
                color: "rgba(255, 255, 255, 0.5)",
                fontStyle: "italic",
                mt: 1,
              }}
            >
              Allowed data types:{" "}
              <Box
                component="span"
                sx={{ color: "secondary.main", fontWeight: 500 }}
              >
                {allowedDtypes.join(", ")}
              </Box>
            </Typography>
          )}
          {/* Restricted data types */}
          {restrictedDtypes?.length > 0 && (
            <Typography
              variant="body2"
              sx={{
                color: "rgba(255, 255, 255, 0.5)",
                fontStyle: "italic",
                mt: 1,
              }}
            >
              Restricted data types:{" "}
              <Box
                component="span"
                sx={{ color: "secondary.main", fontWeight: 500 }}
              >
                {restrictedDtypes.join(", ")}
              </Box>
            </Typography>
          )}
        </Box>
      )}

      {/* Data Grid */}
      <DataGrid
        key={`${datasetColumns.length}-${inputCardinality.exact}-${inputCardinality.max}`}
        autoHeight
        rows={rows}
        columns={columns}
        initialState={{
          pagination: {
            paginationModel: {
              pageSize: 5,
            },
          },
        }}
        disableColumnMenu
        disableColumnFilter
        disableColumnSelector
        disableDensitySelector
        pageSizeOptions={[5, 10, 20]}
        checkboxSelection
        onRowSelectionModelChange={handleSelection}
        rowSelectionModel={rowSelectionModel}
        isRowSelectable={isRowSelectable}
        density="compact"
        getRowClassName={(params) =>
          isRowSelectable(params) === false ? "mui-row-disabled" : ""
        }
        sx={{
          "& .mui-row-disabled": {
            backgroundColor: "rgba(0, 0, 0, 0.12)",
            color: "#777",
          },
        }}
        slots={{
          toolbar: () => (
            <Box sx={{ p: 1 }}>
              <GridToolbarQuickFilter />
            </Box>
          ),
        }}
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
