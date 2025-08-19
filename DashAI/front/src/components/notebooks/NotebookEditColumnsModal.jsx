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
  Button,
} from "@mui/material";
import {
  ArrowBackOutlined,
  ArrowForward,
  ArrowBack,
} from "@mui/icons-material";

import { useSnackbar } from "notistack";
import { getDatasetFile } from "../../api/datasets";
import FormSchemaWithSelectedModel from "../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../shared/FormSchemaContainer";
import ColumnSelectionTable from "../threeSectionLayout/ColumnSelectionTable";

function NotebookEditColumnsModal({
  open,
  onClose,
  explorerData,
  notebook,
  onSelectionChange = () => {},
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [datasetColumns, setDatasetColumns] = useState([]);
  const [currentStep, setCurrentStep] = useState(0); // 0: columns, 1: parameters
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [isSelectionValid, setIsSelectionValid] = useState(false);

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

  // Fetch dataset columns from notebook file
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

  // Reset to first step when modal opens
  useEffect(() => {
    if (open) {
      setCurrentStep(0);
      setSelectedColumns([]);
      setIsSelectionValid(false);
    }
  }, [open]);

  // Handle column selection from the generic table
  const handleColumnSelectionChange = (selectedColumnsData) => {
    setSelectedColumns(selectedColumnsData);
    onSelectionChange(selectedColumnsData);
  };

  // Handle validation changes from the generic table
  const handleValidationChange = (isValid) => {
    setIsSelectionValid(isValid);
  };

  const handleNext = () => {
    if (isSelectionValid) {
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
    enqueueSnackbar("Explorer configured successfully", { variant: "success" });
    onClose();
  };

  const canProceedToNext = () => {
    return isSelectionValid;
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
            // Step 1: Column Selection using ColumnSelectionTable
            <ColumnSelectionTable
              datasetColumns={datasetColumns}
              inputCardinality={inputCardinality}
              allowedDtypes={allowedDtypes}
              restrictedDtypes={restrictedDtypes}
              onSelectionChange={handleColumnSelectionChange}
              onValidationChange={handleValidationChange}
              title={`Select the columns you want to use for the ${explorerType.label} exploration`}
              description=""
            />
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
