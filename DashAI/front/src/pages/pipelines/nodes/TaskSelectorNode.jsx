import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  DialogContent,
  Typography,
  Select,
  MenuItem,
  OutlinedInput,
  Chip,
} from "@mui/material";

const TaskModelSelectorNode = ({ open, onClose, onSave, savedConfig }) => {
  const [selectedTask, setSelectedTask] = useState(savedConfig?.task || "");
  const [selectedModels, setSelectedModels] = useState(savedConfig?.models || []);

  const taskModelOptions = {
    TabularClassificationTask: [
      "SVC",
      "DecisionTreeClassifier",
      "DummyClassifier",
      "HistGradientBoostingClassifier",
      "KNeighborsClassifier",
      "LogisticRegression",
      "RandomForestClassifier",
    ],
    TextClassificationTask: ["text"],
    TranslationTask: ["translation"],
    ImageClassificationTask: ["image"],
  };

  useEffect(() => {
    setSelectedTask(savedConfig?.task || "");
    setSelectedModels(savedConfig?.models || []);
  }, [savedConfig]);

  const handleTaskChange = (event) => {
    setSelectedTask(event.target.value);
    setSelectedModels([]);
  };

  const handleModelChange = (event) => {
    setSelectedModels(event.target.value);
  };

  const saveSelection = () => {
    onSave({ task: selectedTask, models: selectedModels });
    onClose();
  };

  return (
    <DialogContent>
      <Typography variant="body1" gutterBottom>
        Choose the type of task for this pipeline:
      </Typography>
      <Box mt={2}>
        <Select value={selectedTask} onChange={handleTaskChange} displayEmpty fullWidth>
          <MenuItem value="" disabled>
            Select a Task
          </MenuItem>
          {Object.keys(taskModelOptions).map((task) => (
            <MenuItem key={task} value={task}>
              {task.charAt(0).toUpperCase() + task.slice(1)}
            </MenuItem>
          ))}
        </Select>
      </Box>

      {selectedTask && (
        <>
          <Typography variant="body1" gutterBottom mt={3}>
            Choose models:
          </Typography>
          <Box mt={2}>
            <Select
              multiple
              value={selectedModels}
              onChange={handleModelChange}
              displayEmpty
              fullWidth
              input={<OutlinedInput />}
              renderValue={(selected) =>
                selected.length > 0 ? (
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} />
                    ))}
                  </Box>
                ) : (
                  <Typography color="textSecondary">Select Models</Typography>
                )
              }
            >
              {taskModelOptions[selectedTask].map((model) => (
                <MenuItem key={model} value={model}>
                  {model}
                </MenuItem>
              ))}
            </Select>
          </Box>
        </>
      )}

      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={saveSelection}
          disabled={!selectedTask || selectedModels.length === 0}
        >
          Save Selection
        </Button>
      </Box>
    </DialogContent>
  );
};

export default TaskModelSelectorNode;
