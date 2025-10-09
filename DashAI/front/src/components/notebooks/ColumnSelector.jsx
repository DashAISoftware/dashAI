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

  // Handle automatic column selection based on cardinality
  useEffect(() => {
    // Auto-select only once at start if no initial selection provided
    if (rows.length > 0 && rowSelectionModel.length === 0) {
      const validIds = getValidColumnIds();
      let autoSelection = [];

      if (inputCardinality.exact && validIds.length >= inputCardinality.exact) {
        autoSelection = validIds.slice(0, inputCardinality.exact);
      } else if (inputCardinality.max && validIds.length > 0) {
        autoSelection = validIds.slice(
          0,
          Math.min(validIds.length, inputCardinality.max),
        );
      } else if (
        inputCardinality.min &&
        validIds.length >= inputCardinality.min
      ) {
        autoSelection = inputCardinality.max
          ? validIds.slice(0, inputCardinality.min)
          : validIds;
      } else {
        autoSelection = validIds;
      }

      if (autoSelection.length > 0) {
        setRowSelectionModel(autoSelection);
      }
    }
  }, [rows.length]);

  // Validate current selection
  const isValidSelection = useCallback(
    (selection) => {
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
    if (selection.length > inputCardinality.max) {
      selection = selection.slice(0, inputCardinality.max);
    }

    // update order for the rows
    let newRows = rows.map((row) => {
      const order = selection.indexOf(row.id) + 1;
      return { ...row, order };
    });

    setRows(newRows);
    setRowSelectionModel(selection);
  };

  return (
    <Box>
      {/* Cardinality information */}
      <Stack
        direction="row"
        spacing={1}
        sx={{ mb: 1, display: "flex", justifyContent: "space-evenly" }}
      >
        {inputCardinality.min && (
          <Typography variant="body2">
            Minimum number of columns: {inputCardinality.min}
          </Typography>
        )}
        {inputCardinality.exact && (
          <Typography variant="body2">
            Number of columns required: {inputCardinality.exact}
          </Typography>
        )}
        {inputCardinality.max && (
          <Typography variant="body2">
            Maximum number of columns: {inputCardinality.max}
          </Typography>
        )}
      </Stack>

      {/* Allowed data types */}
      {allowedDtypes?.length > 0 && !allowedDtypes.includes("*") && (
        <Box
          sx={{
            mb: 1,
            display: "flex",
            flexDirection: "row",
            gap: 1,
            alignItems: "center",
          }}
        >
          <Typography variant="body2">Allowed data types:</Typography>
          {allowedDtypes.map((dtype) => (
            <Chip key={dtype} label={dtype} color="secondary" size="small" />
          ))}
        </Box>
      )}

      {/* Restricted data types */}
      {restrictedDtypes?.length > 0 && (
        <Box
          sx={{
            mb: 1,
            display: "flex",
            flexDirection: "row",
            gap: 1,
            alignItems: "center",
          }}
        >
          <Typography variant="body2">Restricted data types:</Typography>
          {restrictedDtypes.map((dtype) => (
            <Chip key={dtype} label={dtype} color="error" size="small" />
          ))}
        </Box>
      )}

      {/* Data Grid */}
      <DataGrid
        data-tour="column-selector"
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
        disableRowSelectionOnClick
        onRowSelectionModelChange={handleSelection}
        rowSelectionModel={rowSelectionModel}
        isRowSelectable={isRowSelectable}
        density="compact"
        getRowClassName={(params) => {
          if (isRowSelectable(params) === false) {
            return "mui-row-disabled";
          }
          return "";
        }}
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
