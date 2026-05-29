import React from "react";
import { Box, TextField, Button } from "@mui/material";

function PipelineToolbar({
  pipelineName,
  setPipelineName,
  onRun,
  nameError,
  nameErrorMessage,
  handlePipelineNameChange,
}) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        mb: 4,
      }}
    >
      <TextField
        label="Pipeline Name"
        variant="outlined"
        size="small"
        value={pipelineName}
        onChange={
          handlePipelineNameChange || ((e) => setPipelineName(e.target.value))
        }
        error={nameError}
        helperText={nameErrorMessage}
        sx={{
          mr: 4,
          input: { color: "black" },
          "& .MuiOutlinedInput-root fieldset": { borderColor: "black" },
          "& label": { color: "black" },
        }}
      />
      <Button variant="contained" color="primary" onClick={onRun}>
        Run
      </Button>
    </Box>
  );
}

export default PipelineToolbar;
