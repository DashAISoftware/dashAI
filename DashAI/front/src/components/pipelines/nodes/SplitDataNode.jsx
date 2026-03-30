import React, { useState, useEffect, useRef } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  DialogContent,
  Typography,
  TextField,
  Grid,
  FormControlLabel,
  Checkbox,
} from "@mui/material";
import { getDatasetInfo as getDatasetInfoRequest } from "../../../api/datasets";
import { validateNode } from "../../../api/pipeline";
import { parseRangeToIndex } from "../../../utils/parseRange";
import { useSnackbar } from "notistack";

/**
 * SplitDataNode – configures input/output columns and train/val/test splits.
 *
 * Expects `prevNodes` to contain the DataSelector config (with id & file_path)
 * so it can fetch column metadata from the dataset.
 */
const SplitDataNode = ({ open, onClose, onSave, savedConfig, prevNodes }) => {
  // Column ranges
  const [inputColumns, setInputColumns] = useState(
    savedConfig?.input_columns || "",
  );
  const [outputColumns, setOutputColumns] = useState(
    savedConfig?.output_columns || "",
  );

  // Splits
  const [splits, setSplits] = useState(
    savedConfig?.splits || {
      train: 0.6,
      validation: 0.2,
      test: 0.2,
      shuffle: true,
      stratify: false,
      splitType: "random",
    },
  );

  // Dataset info
  const datasetNode = prevNodes?.find((node) => node?.file_path && node?.id);
  const datasetId = datasetNode?.id ?? null;
  const [datasetInfo, setDatasetInfo] = useState({});
  const [infoLoading, setInfoLoading] = useState(true);

  // Validation
  const [inputError, setInputError] = useState(false);
  const [outputError, setOutputError] = useState(false);
  const [inputErrorMessage, setInputErrorMessage] = useState("");
  const [outputErrorMessage, setOutputErrorMessage] = useState("");
  const [validationStatus, setValidationStatus] = useState("");

  const { enqueueSnackbar } = useSnackbar();
  const hasWarnedRef = useRef(false);

  // ---------- Fetch dataset info ----------
  const getDatasetInfo = async () => {
    setInfoLoading(true);
    try {
      const info = await getDatasetInfoRequest(datasetId);
      setDatasetInfo(info);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain the dataset info.", {
        variant: "error",
      });
      console.error(error);
    } finally {
      setInfoLoading(false);
    }
  };

  useEffect(() => {
    if (!datasetId) {
      setInfoLoading(false);
      if (!hasWarnedRef.current) {
        enqueueSnackbar(
          "Missing dataset – connect a DataSelector node first.",
          {
            variant: "warning",
          },
        );
        hasWarnedRef.current = true;
      }
      return;
    }
    getDatasetInfo();
  }, [datasetId]);

  // ---------- Re-apply saved config when dataset info arrives ----------
  useEffect(() => {
    const total = datasetInfo?.total_columns;
    setInputColumns(
      savedConfig?.input_columns?.join(",") || (total ? `1-${total - 1}` : ""),
    );
    setOutputColumns(
      savedConfig?.output_columns?.join(",") || (total ? `${total}` : ""),
    );
    setSplits(
      savedConfig?.splits || {
        train: 0.6,
        validation: 0.2,
        test: 0.2,
        shuffle: true,
        stratify: false,
        splitType: "random",
      },
    );
  }, [savedConfig, datasetInfo]);

  // ---------- Validate column ranges on change ----------
  useEffect(() => {
    const maxValue = datasetInfo?.total_columns;
    if (!maxValue) return;

    try {
      if (inputColumns) parseRangeToIndex(inputColumns, maxValue);
      setInputError(false);
      setInputErrorMessage("");
    } catch (err) {
      setInputError(true);
      setInputErrorMessage(err.message);
    }

    try {
      if (outputColumns) parseRangeToIndex(outputColumns, maxValue);
      setOutputError(false);
      setOutputErrorMessage("");
    } catch (err) {
      setOutputError(true);
      setOutputErrorMessage(err.message);
    }
  }, [inputColumns, outputColumns, datasetInfo]);

  // ---------- Save ----------
  const handleSave = async () => {
    const maxValue = datasetInfo?.total_columns;
    const columnNames = datasetInfo?.column_names || [];

    const parsedInput = inputColumns
      ? parseRangeToIndex(inputColumns, maxValue)
      : [];
    const parsedOutput = outputColumns
      ? parseRangeToIndex(outputColumns, maxValue)
      : [];

    const inputColumnNames = parsedInput.map(
      (idx) => columnNames[idx - 1] || `Column_${idx}`,
    );
    const outputColumnNames = parsedOutput.map(
      (idx) => columnNames[idx - 1] || `Column_${idx}`,
    );

    const payload = {
      input_columns: parsedInput,
      output_columns: parsedOutput,
      splits: {
        train: splits.train,
        validation: splits.validation,
        test: splits.test,
        shuffle: splits.shuffle,
        stratify: splits.stratify,
        splitType: splits.splitType,
      },
    };

    try {
      const response = await validateNode("SplitData", payload);
      if (response.status === "ok") {
        setValidationStatus("ok");
        onSave(payload);
        onClose();
      } else {
        setValidationStatus("error");
        enqueueSnackbar(response.message || "Validation failed", {
          variant: "error",
        });
      }
    } catch (e) {
      setValidationStatus("error");
      enqueueSnackbar("Error validating node", { variant: "error" });
      console.error(e);
    }
  };

  const splitsSum =
    Number(splits.train) + Number(splits.validation) + Number(splits.test);
  const splitsValid = Math.abs(splitsSum - 1) < 0.001;

  return (
    <DialogContent>
      <Grid container spacing={2}>
        {/* ---- Column selection ---- */}
        <Grid item xs={12}>
          <Typography variant="body1" sx={{ fontWeight: 600 }}>
            Column Selection
          </Typography>
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            label="Input Columns"
            fullWidth
            value={inputColumns}
            onChange={(e) => setInputColumns(e.target.value)}
            margin="normal"
            error={inputError}
            helperText={inputError ? inputErrorMessage : "e.g. 1-4 or 1,3,5"}
          />
        </Grid>

        <Grid item xs={12} md={6}>
          <TextField
            label="Output Columns"
            fullWidth
            value={outputColumns}
            onChange={(e) => setOutputColumns(e.target.value)}
            margin="normal"
            error={outputError}
            helperText={outputError ? outputErrorMessage : "e.g. 5 or 5-6"}
          />
        </Grid>

        {/* ---- Splits ---- */}
        <Grid item xs={12}>
          <Typography variant="body1" sx={{ fontWeight: 600, mt: 1 }}>
            Data Splits
          </Typography>
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            label="Training"
            type="number"
            fullWidth
            value={splits.train}
            onChange={(e) =>
              setSplits({ ...splits, train: parseFloat(e.target.value) })
            }
            margin="normal"
            inputProps={{ step: 0.05, min: 0, max: 1 }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            label="Validation"
            type="number"
            fullWidth
            value={splits.validation}
            onChange={(e) =>
              setSplits({ ...splits, validation: parseFloat(e.target.value) })
            }
            margin="normal"
            inputProps={{ step: 0.05, min: 0, max: 1 }}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            label="Testing"
            type="number"
            fullWidth
            value={splits.test}
            onChange={(e) =>
              setSplits({ ...splits, test: parseFloat(e.target.value) })
            }
            margin="normal"
            inputProps={{ step: 0.05, min: 0, max: 1 }}
          />
        </Grid>

        {!splitsValid && (
          <Grid item xs={12}>
            <Typography variant="caption" color="error">
              Splits must sum to 1.0 (current: {splitsSum.toFixed(2)})
            </Typography>
          </Grid>
        )}

        <Grid item xs={12}>
          <FormControlLabel
            control={
              <Checkbox
                checked={splits.shuffle}
                onChange={(e) =>
                  setSplits({ ...splits, shuffle: e.target.checked })
                }
              />
            }
            label="Shuffle"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={splits.stratify}
                onChange={(e) =>
                  setSplits({ ...splits, stratify: e.target.checked })
                }
              />
            }
            label="Stratify"
          />
        </Grid>
      </Grid>

      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={handleSave}
          disabled={
            infoLoading ||
            inputColumns.length === 0 ||
            outputColumns.length === 0 ||
            inputError ||
            outputError ||
            !splitsValid
          }
        >
          Save
        </Button>
      </Box>
    </DialogContent>
  );
};

SplitDataNode.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
  prevNodes: PropTypes.arrayOf(PropTypes.object),
};

SplitDataNode.defaultProps = {
  savedConfig: null,
  prevNodes: [],
};

export default SplitDataNode;
