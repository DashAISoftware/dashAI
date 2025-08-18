import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";

import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogActions,
  Box,
  IconButton,
  Typography,
  Chip,
  Stack,
  Button,
} from "@mui/material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import {
  ArrowBackOutlined,
  ArrowForward,
  ArrowBack,
} from "@mui/icons-material";

import { useSnackbar } from "notistack";
import {
  getDatasetInfo,
  getDatasetTypes,
  getDatasetFile,
} from "../../api/datasets";
import FormSchemaWithSelectedModel from "../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../shared/FormSchemaContainer";

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
 * Modal to edit columns selection for explorers in notebooks
 * @param {Object} props
 * @param {boolean} props.open - Whether the modal is open
 * @param {Function} props.onClose - Callback to close the modal
 * @param {Object} props.explorerData - Explorer data object
 * @param {Object} props.notebook - Notebook object
 * @param {Function} props.onSelectionChange - Callback for when selection changes
 */
function NotebookEditColumnsModal({
  open,
  onClose,
  explorerData,
  notebook,
  onSelectionChange = () => {},
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [datasetColumns, setDatasetColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [currentStep, setCurrentStep] = useState(0); // 0: columns, 1: parameters
  const [selectedColumns, setSelectedColumns] = useState([]);

  const handleClose = () => {
    onClose();
  };

  const explorer = explorerData?.value || explorerData;
  const allowedDtypes = explorer?.metadata?.allowed_dtypes || [];
  const restrictedDtypes = explorer?.metadata?.restricted_dtypes || [];
  const inputCardinality = explorer?.metadata?.input_cardinality || {};
  const explorerType = {
    value: explorer,
    validColumns: [],
    label: explorer?.metadata?.display_name || explorer?.name,
  };

  // Fetch dataset columns and calculate valid columns
  useEffect(() => {
    const fetchDatasetData = async () => {
      if (open && notebook?.file_path) {
        try {
          // Get a small sample from the notebook's data file to extract column info
          const datasetFile = await getDatasetFile(notebook.file_path, 0, 1);

          if (datasetFile.rows && datasetFile.rows.length > 0) {
            const firstRow = datasetFile.rows[0];
            const columnNames = Object.keys(firstRow);

            const cols = columnNames.map((columnName, index) => {
              const value = firstRow[columnName];
              let dataType = "unknown";
              let valueType = "unknown";

              // Infer types from the sample data
              if (typeof value === "number") {
                dataType = Number.isInteger(value) ? "int64" : "float64";
                valueType = "Value";
              } else if (typeof value === "string") {
                dataType = "object";
                valueType = "Category";
              } else if (typeof value === "boolean") {
                dataType = "bool";
                valueType = "Category";
              }

              return {
                id: index,
                columnName: columnName,
                valueType: valueType,
                dataType: dataType,
                order: 0,
              };
            });
            setDatasetColumns(cols);
          }
        } catch (error) {
          console.error("Error fetching notebook dataset data:", error);
          enqueueSnackbar("Error fetching notebook dataset columns", {
            variant: "error",
          });
        }
      }
    };

    fetchDatasetData();
  }, [open, notebook?.file_path, enqueueSnackbar]);

  useEffect(() => {
    if (datasetColumns.length > 0) {
      let validColumns = datasetColumns;

      if (!allowedDtypes.includes("*")) {
        validColumns = datasetColumns.filter((col) =>
          allowedDtypes.includes(col.dataType),
        );
      }

      if (
        restrictedDtypes.some((dtype) =>
          datasetColumns.some((col) => col.dataType === dtype),
        )
      ) {
        validColumns = validColumns.filter(
          (col) => !restrictedDtypes.includes(col.dataType),
        );
      }

      explorerType.validColumns = validColumns;
      const validColsId = new Set(validColumns.map((col) => col.id));
      const cols = datasetColumns.map((col) => ({
        ...col,
        disabled: !validColsId.has(col.id),
        order: 0,
      }));
      setRows(cols);

      // Auto-select columns based on cardinality
      const validColumnIds = validColumns.map((col) => col.id);
      let autoSelection = [];

      if (
        inputCardinality.exact &&
        validColumnIds.length >= inputCardinality.exact
      ) {
        // If exact cardinality, select exactly that number
        autoSelection = validColumnIds.slice(0, inputCardinality.exact);
      } else if (inputCardinality.max && validColumnIds.length > 0) {
        // If max cardinality, select up to the maximum
        const maxSelectable = Math.min(
          inputCardinality.max,
          validColumnIds.length,
        );
        autoSelection = validColumnIds.slice(0, maxSelectable);
      } else if (
        inputCardinality.min &&
        validColumnIds.length >= inputCardinality.min
      ) {
        // If only min cardinality, select all available columns (or reasonable number)
        autoSelection = validColumnIds;
      } else if (validColumnIds.length > 0) {
        // If no specific cardinality, select all valid columns
        autoSelection = validColumnIds;
      }

      if (autoSelection.length > 0) {
        // Update rows with order
        const updatedCols = cols.map((col) => {
          const order = autoSelection.indexOf(col.id) + 1;
          return { ...col, order };
        });
        setRows(updatedCols);
        setRowSelectionModel(autoSelection);

        // Call selection change callback
        const selectedColumns = updatedCols
          .filter((row) => autoSelection.includes(row.id))
          .sort((a, b) => a.order - b.order)
          .map((row) => ({
            id: row.id,
            columnName: row.columnName,
            valueType: row.valueType,
            dataType: row.dataType,
            order: row.order,
          }));

        onSelectionChange(selectedColumns);
        setSelectedColumns(selectedColumns);
      }
    }
  }, [datasetColumns, explorerData, open]);

  useEffect(() => {
    if (!datasetColumns.length) {
      setRowSelectionModel([]);
    }
    // Reset to first step when modal opens
    setCurrentStep(0);
  }, [open, datasetColumns]);

  const handleSelection = (selection) => {
    if (inputCardinality.max && selection.length > inputCardinality.max) {
      selection = selection.slice(0, inputCardinality.max);
    }

    let newRows = rows.map((row) => {
      const order = selection.indexOf(row.id) + 1;
      return { ...row, order };
    });
    setRows(newRows);
    setRowSelectionModel(selection);

    if (isValidSelection(selection)) {
      const selectedColumnsData = newRows
        .filter((row) => selection.includes(row.id))
        .sort((a, b) => a.order - b.order)
        .map((row) => ({
          id: row.id,
          columnName: row.columnName,
          valueType: row.valueType,
          dataType: row.dataType,
          order: row.order,
        }));

      onSelectionChange(selectedColumnsData);
      setSelectedColumns(selectedColumnsData);
    }
  };

  const isRowSelectable = (params) => {
    if (rowSelectionModel.includes(params.id)) {
      return true;
    }

    if (params.row.disabled) {
      return false;
    }

    const selectedCount = rowSelectionModel.length;
    const maxReached =
      selectedCount >= inputCardinality.max ||
      selectedCount >= inputCardinality.exact;
    if (maxReached) {
      return false;
    }

    return true;
  };

  const isValidSelection = (selection) => {
    if (inputCardinality.exact && selection.length !== inputCardinality.exact) {
      return false;
    }

    if (inputCardinality.min && selection.length < inputCardinality.min) {
      return false;
    }

    if (inputCardinality.max && selection.length > inputCardinality.max) {
      return false;
    }

    return true;
  };

  const handleNext = () => {
    if (isValidSelection(rowSelectionModel)) {
      console.log("=== Explorer Debug for Parameters ===");
      console.log("Full explorerData:", explorerData);
      console.log("Explorer object:", explorer);
      console.log("Explorer type:", explorer?.type);
      console.log("Explorer name:", explorer?.name);
      console.log("Model to configure:", explorer?.name);
      console.log("Notebook file_path:", notebook?.file_path);
      console.log("====================================");
      setCurrentStep(1);
    } else {
      enqueueSnackbar("Please select valid columns before proceeding", {
        variant: "warning",
      });
    }
  };

  const handleBack = () => {
    setCurrentStep(0);
  };

  const handleParametersSubmit = (parameters) => {
    console.log("Parameters submitted:", parameters);
    console.log("Selected columns:", selectedColumns);
    // Here you can handle the final submission with both columns and parameters
    enqueueSnackbar("Explorer configured successfully", { variant: "success" });
    onClose();
  };

  const canProceedToNext = () => {
    return isValidSelection(rowSelectionModel);
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      PaperProps={{
        sx: {
          width: { md: 820, lg: 1000 },
          maxHeight: { lg: 700, xl: "auto" },
          maxWidth: 2000,
          transition: "width 0.3s ease, height 0.3s ease",
        },
      }}
    >
      <DialogTitle>
        <Box display="flex" alignItems="center">
          <IconButton onClick={handleClose}>
            <ArrowBackOutlined />
          </IconButton>
          <Typography variant="h5" sx={{ ml: 2 }}>
            Configure {explorerType.label} -{" "}
            {currentStep === 0 ? "Column Selection" : "Parameters"}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ height: "100%", width: "100%" }}>
          {currentStep === 0 ? (
            // Step 1: Column Selection
            <>
              <Typography
                variant="body1"
                sx={{ mb: 2, whiteSpace: "pre-line" }}
              >
                {`Select the columns you want to use for the ${explorerType.label} exploration`}
              </Typography>

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
                    <Chip
                      key={dtype}
                      label={dtype}
                      color="secondary"
                      size="small"
                    />
                  ))}
                </Box>
              )}
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
                  <Typography variant="body2">
                    Restricted data types:
                  </Typography>
                  {restrictedDtypes.map((dtype) => (
                    <Chip
                      key={dtype}
                      label={dtype}
                      color="error"
                      size="small"
                    />
                  ))}
                </Box>
              )}

              <DataGrid
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
                pageSizeOptions={[5, 10, 20]}
                checkboxSelection
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
                  toolbar: GridToolbar,
                }}
                slotProps={{
                  toolbar: {
                    showQuickFilter: true,
                  },
                }}
              />
            </>
          ) : (
            // Step 2: Parameters Configuration
            <FormSchemaContainer>
              <FormSchemaWithSelectedModel
                onFormSubmit={handleParametersSubmit}
                modelToConfigure={explorer?.name}
                initialValues={{}}
                onCancel={handleBack}
                saveButtonText="SAVE AND RUN"
              />
            </FormSchemaContainer>
          )}
        </Box>
      </DialogContent>

      {currentStep === 0 && (
        <DialogActions sx={{ p: 2, justifyContent: "space-between" }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={handleClose}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button
            endIcon={<ArrowForward />}
            onClick={handleNext}
            variant="contained"
            disabled={!canProceedToNext()}
          >
            Next: Configure Parameters
          </Button>
        </DialogActions>
      )}
    </Dialog>
  );
}

NotebookEditColumnsModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  explorerData: PropTypes.object,
  notebook: PropTypes.object,
  onSelectionChange: PropTypes.func,
};

export default NotebookEditColumnsModal;
