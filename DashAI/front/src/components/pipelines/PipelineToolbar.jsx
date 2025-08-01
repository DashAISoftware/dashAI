import React from "react";
import { Box, TextField, Button } from "@mui/material";

function PipelineToolbar({ 
  pipelineName, 
  setPipelineName, 
  onRun 
}) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
      <TextField
        label="Pipeline Name"
        variant="outlined"
        size="small"
        value={pipelineName}
        onChange={(e) => setPipelineName(e.target.value)}
        sx={{
          mr: 2,
          input: { color: 'black' },
          '& .MuiOutlinedInput-root fieldset': { borderColor: 'black' },
          '& label': { color: 'black' },
        }}
      />
      <Button
        variant="contained"
        color="primary"
        onClick={onRun}
      >
        Run
      </Button>
    </Box>
  );
}

export default PipelineToolbar; 