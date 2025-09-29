import { useState, useEffect } from "react";
import {
  Typography,
  Button,
  Slider,
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

export function SplitSelector({
  onSelectionChange,
  initialSplit,
  initialPercentage,
}) {
  const [selectedSplit, setSelectedSplit] = useState(initialSplit || "test");
  const [percentage, setPercentage] = useState(initialPercentage ?? 20);

  // Propagate changes
  useEffect(() => {
    onSelectionChange({ split: selectedSplit, percentage });
  }, [selectedSplit, percentage]);

  const handleSelectAll = () => {
    setSelectedSplit("all");
    setPercentage(100);
  };

  const handleSliderChange = (_, newValue) => {
    setPercentage(newValue);
  };

  const handleInputChange = (e) => {
    const val = e.target.value === "" ? "" : Number(e.target.value);
    if (val === "" || (val >= 0 && val <= 100)) {
      setPercentage(val);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <FormControl component="fieldset" sx={{ mb: 3, width: "100%" }}>
        <FormLabel component="legend">Dataset Split</FormLabel>

        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mt: 1 }}
        >
          <RadioGroup
            row
            value={selectedSplit}
            onChange={(e) => setSelectedSplit(e.target.value)}
          >
            <FormControlLabel value="train" control={<Radio />} label="Train" />
            <FormControlLabel value="test" control={<Radio />} label="Test" />
            <FormControlLabel
              value="validation"
              control={<Radio />}
              label="Validation"
            />
            <FormControlLabel value="all" control={<Radio />} label="All" />
          </RadioGroup>

          <Button variant="outlined" size="small" onClick={handleSelectAll}>
            Select All
          </Button>
        </Stack>
      </FormControl>

      <Stack spacing={2} mb={2}>
        <Typography gutterBottom>Percentage of Split to Use</Typography>

        <Stack direction="row" spacing={2} alignItems="center">
          <Slider
            value={typeof percentage === "number" ? percentage : 0}
            onChange={handleSliderChange}
            aria-labelledby="percentage-slider"
            valueLabelDisplay="auto"
            step={1}
            marks={[
              { value: 0, label: "0%" },
              { value: 25, label: "25%" },
              { value: 50, label: "50%" },
              { value: 75, label: "75%" },
              { value: 100, label: "100%" },
            ]}
            min={0}
            max={100}
            sx={{ flex: 1 }}
          />

          <TextField
            label="%"
            type="number"
            size="small"
            value={percentage}
            onChange={handleInputChange}
            inputProps={{ min: 0, max: 100 }}
            sx={{ width: "80px" }}
          />
        </Stack>
      </Stack>

      <Divider sx={{ my: 1 }} />

      <Box mt={1}>
        <Typography variant="caption" color="text.secondary">
          Selected split: <strong>{selectedSplit}</strong> | Percentage:{" "}
          {percentage}%
        </Typography>
      </Box>
    </Box>
  );
}
