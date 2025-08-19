import { useState, useEffect } from "react";
import {
  Typography,
  Button,
  TextField,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Box,
  Stack,
  Divider,
} from "@mui/material";

export function RowSelector({ totalRows, onSelectionChange, initialRows }) {
  const [selectedRows, setSelectedRows] = useState([]);
  const [selectionMode, setSelectionMode] = useState("range");
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const [indicesInput, setIndicesInput] = useState("");

  // Initialize selection
  useEffect(() => {
    if (initialRows) {
      if (initialRows.length === 0) {
        setSelectedRows([]); // all
      } else {
        const valid = initialRows.filter(
          (i) => !isNaN(i) && i >= 0 && i < totalRows,
        );
        setSelectedRows(valid);
        setIndicesInput(valid.join(","));
        if (valid.length > 1) {
          setRangeStart(String(valid[0]));
          setRangeEnd(String(valid[valid.length - 1]));
        }
      }
    }
  }, []);

  // Propagate changes
  useEffect(() => {
    onSelectionChange(selectedRows);
  }, [selectedRows]);

  const handleSelectAllRows = () => {
    setSelectedRows([]); // all
  };

  const handleRangeChange = (start, end) => {
    setRangeStart(start);
    setRangeEnd(end);

    const s = parseInt(start, 10);
    const e = parseInt(end, 10);

    if (!isNaN(s) && !isNaN(e) && s >= 0 && e >= s && e < totalRows) {
      const rows = Array.from({ length: e - s + 1 }, (_, i) => s + i);
      if (rows.length === totalRows) {
        setSelectedRows([]); // all
      } else {
        setSelectedRows(rows);
      }
    } else {
      setSelectedRows([]);
    }
  };

  const handleIndicesChange = (value) => {
    setIndicesInput(value);

    if (value.trim().toLowerCase() === "all") {
      setSelectedRows([]); // all
      return;
    }

    const indices = value
      .split(",")
      .map((v) => parseInt(v.trim(), 10))
      .filter((n) => !isNaN(n) && n >= 0 && n < totalRows);

    if (indices.length === totalRows) {
      setSelectedRows([]); // all
    } else {
      setSelectedRows(indices);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" spacing={1} mb={2}>
        <Button variant="outlined" size="small" onClick={handleSelectAllRows}>
          Select All
        </Button>
      </Stack>

      <Divider sx={{ my: 2 }} />

      <FormControl component="fieldset" sx={{ mb: 3 }}>
        <FormLabel component="legend">Selection Mode</FormLabel>
        <RadioGroup
          row
          value={selectionMode}
          onChange={(e) => setSelectionMode(e.target.value)}
        >
          <FormControlLabel
            value="range"
            control={<Radio />}
            label="By Range"
          />
          <FormControlLabel
            value="indices"
            control={<Radio />}
            label="By Indices"
          />
        </RadioGroup>
      </FormControl>

      {selectionMode === "range" ? (
        <Stack spacing={2}>
          <Stack direction="row" spacing={2}>
            <TextField
              label="Start Index"
              type="number"
              size="small"
              value={rangeStart}
              onChange={(e) => handleRangeChange(e.target.value, rangeEnd)}
              inputProps={{ min: 0, max: totalRows - 1 }}
              fullWidth
            />
            <TextField
              label="End Index"
              type="number"
              size="small"
              value={rangeEnd}
              onChange={(e) => handleRangeChange(rangeStart, e.target.value)}
              inputProps={{ min: 0, max: totalRows - 1 }}
              fullWidth
            />
          </Stack>
        </Stack>
      ) : (
        <Stack spacing={2}>
          <TextField
            label="Indices (comma separated, or type 'all')"
            placeholder="0,1,2,5,10 or all"
            value={indicesInput}
            onChange={(e) => handleIndicesChange(e.target.value)}
            fullWidth
            size="small"
          />
        </Stack>
      )}

      <Box mt={2}>
        <Typography variant="caption" color="text.secondary">
          Selected rows:{" "}
          {selectedRows.length === 0
            ? "all"
            : selectedRows.length > 0
            ? selectedRows.join(", ")
            : "None"}
        </Typography>
      </Box>
    </Box>
  );
}
