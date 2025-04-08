import React, { useState, useEffect } from "react";
import { Box, Button, DialogContent, Typography, Checkbox, FormControlLabel, FormGroup } from "@mui/material";
import { validateNode } from "../../../api/pipeline";

const DataExplorationNode = ({ open, onClose, onSave, savedConfig, data }) => {
  const explorationOptions = [
    "shape",
    "columns",
    "dtypes",
    "null_values",
    "unique_values",
  ];

  const [selectedOptions, setSelectedOptions] = useState(savedConfig?.options || []);

  useEffect(() => {
    setSelectedOptions(savedConfig?.options || []);
  }, [savedConfig]);

  const handleOptionChange = (option) => {
    setSelectedOptions((prevOptions) =>
      prevOptions.includes(option)
        ? prevOptions.filter((opt) => opt !== option)
        : [...prevOptions, option]
    );
  };

  const saveExplorationOptions = async () => {
    const dataloaderKey = Object.keys(data).find((key) => key.startsWith("DataLoader"));
    const dataloaderNode = data[dataloaderKey];
    const config = {
      options: selectedOptions,
      dataloader: dataloaderNode,
    };

    const validationResponse = await validateNode("DataExploration", config);

    if (validationResponse.status === "ok") {
      console.log("Node validated successfully");
      onSave({ options: selectedOptions });
      onClose();
    } else {
      console.error("Validation failed:", validationResponse.message);
    }
  };

  return (
    <DialogContent>
      <Typography variant="body1" gutterBottom>
        Choose the data exploration options:
      </Typography>
      <Box mt={2}>
        <FormGroup>
          {explorationOptions.map((option) => (
            <FormControlLabel
              key={option}
              control={
                <Checkbox
                  checked={selectedOptions.includes(option)}
                  onChange={() => handleOptionChange(option)}
                />
              }
              label={option}
            />
          ))}
        </FormGroup>
      </Box>
      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={saveExplorationOptions}
          disabled={selectedOptions.length === 0}
        >
          Save Exploration Options
        </Button>
      </Box>
    </DialogContent>
  );
};

export default DataExplorationNode;
