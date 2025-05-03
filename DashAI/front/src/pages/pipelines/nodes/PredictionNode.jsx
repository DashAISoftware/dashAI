import React from "react";
import { Button, Paper, Typography } from "@mui/material";

function PredictionNode({ onClose, onSave }) {
  const handleSave = () => {
    const nodeData = {
      status: "ok",
    };
    onSave(nodeData);
    onClose();
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Predictions Node
      </Typography>
      <Typography variant="body2" gutterBottom>
        This node will generate predictions using the trained model.
      </Typography>

      <Button variant="contained" onClick={handleSave}>
        Save
      </Button>
    </Paper>
  );
}

export default PredictionNode;
