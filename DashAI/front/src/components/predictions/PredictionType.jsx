import React, { useState, useEffect } from "react";
import {
  Typography,
  RadioGroup,
  Radio,
  Stack,
  FormControlLabel,
  FormControl,
} from "@mui/material";

import DatasetSelector from "./DatasetSelector";
import ManualInput from "./ManualInput";

export default function PredictionType({
  runId,
  datasets,
  columns,
  loading,
  requestError,
  setDatasetsSelected,
  datasetsSelected,
  setManualInputData,
}) {
  const [manualInput, setManualInput] = useState(false);

  return (
    <>
      <FormControl component="fieldset" sx={{ mb: 3, width: "100%" }}>
        <Typography variant="h7" gutterBottom>
          Select Prediction Input Type
        </Typography>

        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mt: 1 }}
        >
          <RadioGroup
            row
            value={manualInput ? "mi" : "ds"}
            onChange={(e) => {
              setManualInput(e.target.value === "mi");
              if (e.target.value === "ds") {
                setManualInputData(null);
              }
            }}
          >
            <FormControlLabel
              value="ds"
              control={<Radio />}
              label="Dataset Selector"
            />
            <FormControlLabel
              value="mi"
              control={<Radio />}
              label="Manual Input"
            />
          </RadioGroup>
        </Stack>
      </FormControl>

      {manualInput ? (
        <ManualInput runId={runId} />
      ) : (
        <DatasetSelector
          datasets={datasets}
          columns={columns}
          loading={loading}
          requestError={requestError}
          setDatasetsSelected={setDatasetsSelected}
          datasetsSelected={datasetsSelected}
        />
      )}
    </>
  );
}
