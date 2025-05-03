import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  DialogContent,
  Typography,
  TextField,
} from "@mui/material";

const SplitData = ({ open, onClose, onSave, savedConfig }) => {
  const [inputColumns, setInputColumns] = useState(savedConfig?.input_columns || []);
  const [outputColumns, setOutputColumns] = useState(savedConfig?.output_columns || []);
  const [splits, setSplits] = useState(
    savedConfig?.splits || { train: 60, validation: 20, test: 20, shuffle: true, stratify: false, splitType: "random" }
  );

  useEffect(() => {
    setInputColumns(savedConfig?.input_columns || []);
    setOutputColumns(savedConfig?.output_columns || []);
    setSplits(savedConfig?.splits || { train: 60, validation: 20, test: 20, shuffle: true, stratify: false, splitType: "random" });
  }, [savedConfig]);

  const parseArrayInput = (value) =>
    value
      .split(",")
      .map((v) => v.trim())
      .filter((v) => v.length > 0);

  const handleSave = () => {
    onSave({
      input_columns: ["SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm"],
      output_columns: ["Species"],
      splits: {
        train: splits.train / 100,
        validation: splits.validation / 100,
        test: splits.test / 100,
        shuffle: splits.shuffle,
        stratify: splits.stratify,
        splitType: splits.splitType
      }
    });
    onClose();
  };

  return (
    <DialogContent>
      <Typography variant="body1" gutterBottom>
        Configure Dataset Parameters:
      </Typography>

      <Box mt={2}>
        <TextField
          label="Input Columns (comma-separated)"
          fullWidth
          value={inputColumns.join(", ")}
          onChange={(e) => setInputColumns(parseArrayInput(e.target.value))}
        />
      </Box>

      <Box mt={2}>
        <TextField
          label="Output Columns (comma-separated)"
          fullWidth
          value={outputColumns.join(", ")}
          onChange={(e) => setOutputColumns(parseArrayInput(e.target.value))}
        />
      </Box>

      <Box mt={3}>
        <Typography variant="body2" gutterBottom>
          Data Splits (sum should be 100):
        </Typography>
        <TextField
          label="Training (%)"
          type="number"
          fullWidth
          value={splits.train}
          onChange={(e) =>
            setSplits({ ...splits, train: parseInt(e.target.value, 10) })
          }
          margin="normal"
        />
        <TextField
          label="Validation (%)"
          type="number"
          fullWidth
          value={splits.validation}
          onChange={(e) =>
            setSplits({ ...splits, validation: parseInt(e.target.value, 10) })
          }
          margin="normal"
        />
        <TextField
          label="Testing (%)"
          type="number"
          fullWidth
          value={splits.test}
          onChange={(e) =>
            setSplits({ ...splits, test: parseInt(e.target.value, 10) })
          }
          margin="normal"
        />
      </Box>

      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={handleSave}
          disabled={
            inputColumns.length === 0 ||
            outputColumns.length === 0 ||
            splits.train + splits.validation + splits.test !== 100
          }
        >
          Save Configuration
        </Button>
      </Box>
    </DialogContent>
  );
};

export default SplitData;
