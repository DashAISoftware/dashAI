import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
  MenuItem,
  TextField,
  Box,
  Typography,
} from "@mui/material";
import { Close as CloseIcon } from "@mui/icons-material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { getComponents as getComponentsRequest } from "../../../api/component";
import ColumnSelector from "../../notebooks/ColumnSelector";
import ParameterStepConverter from "../../notebooks/converterCreation/ParameterStepConverter";

/**
 * Simple dialog to add one converter to a session (fit-on-train preprocessing,
 * see SessionPreprocessingJob on the backend). Unlike the notebook converter
 * flow, there's no row scope or target column here: the "scope" is already
 * the session's train split, and the target is already fixed by the
 * session's output columns.
 */
function AddSessionConverterDialog({
  open,
  onClose,
  inputColumns,
  columnTypes,
  onAddConverter,
}) {
  const { t } = useTranslation(["models", "datasets", "common"]);
  const { enqueueSnackbar } = useSnackbar();

  const [converters, setConverters] = useState([]);
  const [loadingConverters, setLoadingConverters] = useState(true);
  const [selectedConverterName, setSelectedConverterName] = useState("");
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [columnsValid, setColumnsValid] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoadingConverters(true);
    getComponentsRequest({ selectTypes: ["Converter"] })
      .then((data) => setConverters(data || []))
      .catch((error) => {
        console.error("Error fetching converters:", error);
        enqueueSnackbar(t("datasets:error.errorFetchingTools"), {
          variant: "error",
        });
      })
      .finally(() => setLoadingConverters(false));
  }, [open]);

  useEffect(() => {
    if (!open) {
      setSelectedConverterName("");
      setSelectedColumns([]);
      setColumnsValid(false);
    }
  }, [open]);

  const selectedTool = converters.find(
    (tool) => tool.name === selectedConverterName,
  );

  // Only input columns can be transformed by a session converter: the
  // output column is never part of X, and the model session's split is
  // already the "scope" (no arbitrary row scope like in notebooks).
  const inputColumnTypes = Object.fromEntries(
    Object.entries(columnTypes || {}).filter(([name]) =>
      inputColumns.includes(name),
    ),
  );

  const handleClose = () => {
    setSelectedConverterName("");
    setSelectedColumns([]);
    onClose();
  };

  const handleSaveConverter = (params) => {
    if (selectedColumns.length === 0) {
      enqueueSnackbar(t("models:error.noColumnsSelectedForConverter"), {
        variant: "warning",
      });
      return;
    }
    onAddConverter({
      converter: selectedConverterName,
      params: params || {},
      columns: selectedColumns.map((col) => col.columnName),
    });
    handleClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {t("models:button.addConverter")}
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <TextField
            select
            label={t("datasets:label.converter")}
            value={selectedConverterName}
            onChange={(e) => {
              setSelectedConverterName(e.target.value);
              setSelectedColumns([]);
            }}
            fullWidth
            size="small"
            disabled={loadingConverters}
          >
            {converters.map((tool) => (
              <MenuItem key={tool.name} value={tool.name}>
                {tool.display_name ?? tool.name}
              </MenuItem>
            ))}
          </TextField>

          {!selectedConverterName && (
            <Typography variant="body2" color="text.secondary">
              {t("models:label.selectConverterFirst")}
            </Typography>
          )}

          {selectedTool && (
            <>
              <ColumnSelector
                file_path=""
                tool={selectedTool}
                columnTypes={inputColumnTypes}
                allowedTypes={selectedTool.metadata?.allowed_types || []}
                allowedDtypes={selectedTool.metadata?.allowed_dtypes || []}
                nonAllowedDtypes={
                  selectedTool.metadata?.non_allowed_dtypes || []
                }
                onSelectionChange={setSelectedColumns}
                onValidationChange={setColumnsValid}
              />

              {columnsValid && (
                <ParameterStepConverter
                  converter={selectedTool.name}
                  tool={selectedTool}
                  selectedColumns={selectedColumns}
                  initialParams={{}}
                  handleSaveConverter={handleSaveConverter}
                  setStep={handleClose}
                />
              )}
            </>
          )}
        </Box>
      </DialogContent>
      <DialogActions sx={{ p: 4 }}>
        <Button variant="outlined" onClick={handleClose}>
          {t("common:cancel")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

AddSessionConverterDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  inputColumns: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnTypes: PropTypes.object,
  onAddConverter: PropTypes.func.isRequired,
};

export default AddSessionConverterDialog;
