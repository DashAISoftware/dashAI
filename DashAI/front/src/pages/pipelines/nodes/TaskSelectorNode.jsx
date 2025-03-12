import React, { useState, useEffect } from "react";
import { Box, Button, DialogContent, Typography, Select, MenuItem } from "@mui/material";

const TaskSelectorNode = ({ open, onClose, onSave, savedTask }) => {
  const [selectedTask, setSelectedTask] = useState(savedTask || "");

  useEffect(() => {
    setSelectedTask(savedTask || "");
  }, [savedTask]);

  const handleTaskChange = (event) => {
    setSelectedTask(event.target.value);
  };

  const saveTaskSelection = () => {
    onSave({ task: selectedTask });
    onClose();
  };

  return (
    <DialogContent>
      <Typography variant="body1" gutterBottom>
        Choose the type of task for this pipeline:
      </Typography>
      <Box mt={2}>
        <Select
          value={selectedTask}
          onChange={handleTaskChange}
          displayEmpty
          fullWidth
        >
          <MenuItem value="" disabled>
            Select a Task
          </MenuItem>
          <MenuItem value="classification">Classification</MenuItem>
          <MenuItem value="regression">Regression</MenuItem>
          <MenuItem value="clustering">Clustering</MenuItem>
          <MenuItem value="time_series">Time Series Forecasting</MenuItem>
        </Select>
      </Box>
      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={saveTaskSelection}
          disabled={!selectedTask}
        >
          Save Task
        </Button>
      </Box>
    </DialogContent>
  );
};

export default TaskSelectorNode;
