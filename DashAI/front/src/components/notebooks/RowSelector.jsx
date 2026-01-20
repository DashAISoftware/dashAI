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
import { useTheme } from "@mui/material/styles";

export function RowSelector({ totalRows, onSelectionChange, initialRows }) {
  const theme = useTheme();
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
        setRangeStart("1");
        setRangeEnd(String(totalRows));
        setIndicesInput("all");
      } else {
        const valid = initialRows.filter(
          (i) => !isNaN(i) && i >= 0 && i <= totalRows,
        );
        setSelectedRows(valid);
        setIndicesInput(valid.join(","));
        if (valid.length > 0) {
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
    setRangeStart("1");
    setRangeEnd(String(totalRows));
    setIndicesInput("all");
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
        setIndicesInput("all");
      } else {
        setSelectedRows(rows);
        setIndicesInput(rows.join(","));
      }
    } else {
      setSelectedRows([]);
      setIndicesInput("");
    }
  };

  const handleIndicesChange = (value) => {
    setIndicesInput(value);

    if (value.trim().toLowerCase() === "all") {
      setSelectedRows([]); // all
      setRangeStart("1");
      setRangeEnd(String(totalRows));
      return;
    }

    const indices = value
      .split(",")
      .map((v) => parseInt(v.trim(), 10))
      .filter((n) => !isNaN(n) && n >= 0 && n < totalRows);

    if (indices.length === totalRows) {
      setSelectedRows([]); // all
      setRangeStart("1");
      setRangeEnd(String(totalRows));
    } else {
      setSelectedRows(indices);
      if (indices.length > 0) {
        setRangeStart(String(indices[0]));
        setRangeEnd(String(indices[indices.length - 1]));
      } else {
        setRangeStart("");
        setRangeEnd("");
      }
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <FormControl component="fieldset" sx={{ mb: 3, width: "100%" }}>
        <FormLabel component="legend">Selection Mode</FormLabel>

        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mt: 1 }}
        >
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

          <Button variant="outlined" size="small" onClick={handleSelectAllRows}>
            Select All
          </Button>
        </Stack>
      </FormControl>
      {selectionMode === "range" ? (
        <Stack spacing={2} mb={2}>
          <Stack direction="row" spacing={2}>
            <TextField
              label="Start Index"
              type="number"
              size="small"
              value={rangeStart}
              onChange={(e) => handleRangeChange(e.target.value, rangeEnd)}
              fullWidth
              slotProps={{
                htmlInput: { min: 0, max: totalRows - 1 },
              }}
            />
            <TextField
              label="End Index"
              type="number"
              size="small"
              value={rangeEnd}
              onChange={(e) => handleRangeChange(rangeStart, e.target.value)}
              fullWidth
              slotProps={{
                htmlInput: { min: 0, max: totalRows - 1 },
              }}
            />
          </Stack>
        </Stack>
      ) : (
        <Stack spacing={2} mb={2}>
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
      <Divider sx={{ my: 1 }} />
      <Box mt={1}>
        <Typography
          variant="caption"
          sx={{ color: theme.palette.text.secondary }}
        >
          Selected rows:{" "}
          {selectedRows.length === 0
            ? "all"
            : selectedRows.length > 0
              ? selectedRows.join(", ")
              : "None"}{" "}
          | Total rows: {totalRows}
        </Typography>
      </Box>
    </Box>
  );
}
