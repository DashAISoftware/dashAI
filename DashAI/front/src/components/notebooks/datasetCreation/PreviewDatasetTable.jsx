import { useMemo, useState } from "react";
import { Typography, Select, MenuItem, Box } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { TypeChangeValidator } from "./TypeChangeValidator";

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
  // Boolean: "bool",  // Boolean is always Categorical
};

/**
 * Table component to display dataset preview with inferred types in column headers.
 *
 * @param {Array} rows - Array of row objects to display
 * @param {Object} columnTypes - Object mapping column names to their inferred types
 *                                (e.g., { columnName: { type: "Categorical", dtype: "string" } })
 * @param {File} file - The uploaded file (needed for validation)
 * @param {Object} params - Dataloader parameters (needed for validation)
 * @param {Function} onTypeChange - Callback when types are successfully changed
 */
export default function PreviewDatasetTable({
  rows,
  columnTypes,
  file,
  params,
  onTypeChange,
}) {
  const [showValidator, setShowValidator] = useState(false);
  const [pendingChanges, setPendingChanges] = useState({});

  const handleTypeChangeRequest = (columnName, newType) => {
    const currentType = columnTypes[columnName]?.type;

    if (currentType === newType) {
      return;
    }

    const newDtype = TYPE_TO_DEFAULT_DTYPE[newType] || "string";

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

  const columns = useMemo(() => {
    if (!rows || rows.length === 0) return [];

    const firstRow = rows[0];
    return Object.keys(firstRow).map((field) => {
      const columnType = columnTypes[field];

      return {
        field,
        headerName: field,
        minWidth: 150,
        flex: 1,
        renderHeader: () => (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              width: "100%",
              gap: 0.5,
            }}
          >
            <Typography
              variant="subtitle2"
              sx={{
                fontWeight: 600,
                fontSize: "0.875rem",
              }}
            >
              {field}
            </Typography>

            <Select
              value={columnType?.type || "Text"}
              onChange={(e) => handleTypeChangeRequest(field, e.target.value)}
              size="small"
              sx={{
                fontSize: "0.75rem",
                minWidth: 120,
                "& .MuiSelect-select": {
                  paddingY: 0.5,
                  paddingX: 1,
                },
              }}
            >
              <MenuItem value="Integer">Integer</MenuItem>
              <MenuItem value="Float">Float</MenuItem>
              <MenuItem value="Text">Text</MenuItem>
              <MenuItem value="Categorical">Categorical</MenuItem>
            </Select>
          </Box>
        ),
      };
    });
  }, [rows, columnTypes]);

  const rowsWithIds = useMemo(() => {
    if (!rows) return [];
    return rows.map((row, index) => ({
      id: row.id !== undefined ? row.id : index,
      ...row,
    }));
  }, [rows]);

  return (
    <>
      <DataGrid
        rows={rowsWithIds}
        columns={columns}
        autoHeight
        density="compact"
        disableRowSelectionOnClick
        initialState={{
          pagination: { paginationModel: { pageSize: 5 } },
        }}
        pageSizeOptions={[5, 10, 25]}
        columnHeaderHeight={100}
        sx={{
          "& .MuiDataGrid-columnHeader": {
            backgroundColor: "rgba(0, 0, 0, 0.02)",
          },
        }}
      />

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
