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
import { Trans, useTranslation } from "react-i18next";

export function SplitSelector({
  totalRows,
  splits,
  onSelectionChange,
  initialSplit,
  initialPercentage,
}) {
  const [selectedSplit, setSelectedSplit] = useState(initialSplit || "test");
  const [percentage, setPercentage] = useState(initialPercentage ?? 20);
  const { t } = useTranslation(["explainers", "common"]);

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
    <Box sx={{ p: 6 }}>
      <FormControl component="fieldset" sx={{ mb: 6, width: "100%" }}>
        <FormLabel component="legend">
          {t("explainers:label.datasetSplit")}
        </FormLabel>

        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mt: 2 }}
        >
          <RadioGroup
            row
            value={selectedSplit}
            onChange={(e) => setSelectedSplit(e.target.value)}
          >
            <FormControlLabel
              value="train"
              control={<Radio />}
              label={t("common:train")}
            />
            <FormControlLabel
              value="test"
              control={<Radio />}
              label={t("common:test")}
            />
            <FormControlLabel
              value="validation"
              control={<Radio />}
              label={t("common:validation")}
            />
            <FormControlLabel
              value="all"
              control={<Radio />}
              label={t("common:all")}
            />
          </RadioGroup>

          <Button variant="outlined" size="small" onClick={handleSelectAll}>
            {t("common:selectAll")}
          </Button>
        </Stack>
      </FormControl>

      <Stack spacing={4} mb={4}>
        <Typography gutterBottom>
          {t("explainers:label.percentageOfSplitToUse")}
        </Typography>

        <Stack direction="row" spacing={4} alignItems="center">
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

      <Divider sx={{ my: 2 }} />

      <Box mt={2}>
        <Typography variant="caption" color="text.secondary">
          <Trans i18nKey="explainers:label.splitSelectionSummary">
            Percentage: {{ percentage }}% | Rows selected:
            {{
              rowsSelected:
                percentage != 0
                  ? Math.round(
                      (percentage / 100) * (totalRows * splits[selectedSplit]),
                    )
                  : 1,
            }}
            / {{ totalRows: Math.round(totalRows * splits[selectedSplit]) }}
          </Trans>
        </Typography>
      </Box>
    </Box>
  );
}
