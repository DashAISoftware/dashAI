import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  DialogContent,
  Typography,
  TextField,
  MenuItem,
  Grid,
  IconButton,
} from "@mui/material";
import SettingsIcon from "@mui/icons-material/Settings";
import useSchema from "../../../hooks/useSchema";
import ParamsSettings from "./ParamsSettings";

const Train = ({ open, onClose, onSave, savedConfig }) => {
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

  const availableMetrics = {
    TabularClassificationTask: ["Accuracy", "F1", "Precision", "Recall"],
    TextClassificationTask: ["Accuracy", "F1", "Precision", "Recall"],
    TranslationTask: ["Bleu", "Ter"],
    ImageClassificationTask: ["Accuracy", "F1"],
  };

  const [inputColumns, setInputColumns] = useState(savedConfig?.input_columns || []);
  const [outputColumns, setOutputColumns] = useState(savedConfig?.output_columns || []);
  const [splits, setSplits] = useState(
    savedConfig?.splits || { train: 60, validation: 20, test: 20, shuffle: true, stratify: false, splitType: "random" }
  );
  const [task, setTask] = useState(savedConfig?.task || "");
  const [model, setModel] = useState(savedConfig?.models || "");
  const [metrics, setMetrics] = useState(savedConfig?.metrics || []);
  const [openSettings, setOpenSettings] = useState(false);
  const [modelParams, setModelParams] = useState({});

  const {
    defaultValues,
    modelSchema,
    yupSchema,
    loading,
  } = useSchema({ modelName: model });

  useEffect(() => {
    setInputColumns(savedConfig?.input_columns || ["1-4"]);
    setOutputColumns(savedConfig?.output_columns || ["5"]);
    setSplits(savedConfig?.splits || { train: 60, validation: 20, test: 20, shuffle: true, stratify: false, splitType: "random" });
    setTask(savedConfig?.task || "");
    setModel(savedConfig?.models || "");
    setMetrics(savedConfig?.metrics || []);
  }, [savedConfig]);

  useEffect(() => {
    if (
        defaultValues &&
        Object.keys(defaultValues).length > 0 &&
        Object.keys(modelParams).length === 0
      ) {
        setModelParams(defaultValues);
      }
    }, [defaultValues]);

  const parseArray = (input) => {
    const items = typeof input === 'string'
      ? input.replace(/[\[\]\s]/g, '').split(',')
      : input.map(String);

    return items.flatMap(item => {
      if (!item.includes('-')) return [+item];
      const [start, end] = item.split('-').map(Number);
      return Array.from({ length: (end || start) - start + 1 }, (_, i) => start + i);
    });
  };

  const handleChange = (newValues) => {
    setModelParams(newValues);
  };

  const handleSave = () => {
    onSave({
      input_columns: parseArray(inputColumns),
      output_columns: parseArray(outputColumns),
      splits: {
        train: splits.train / 100,
        validation: splits.validation / 100,
        test: splits.test / 100,
        shuffle: splits.shuffle,
        stratify: splits.stratify,
        splitType: splits.splitType,
      },
      task: task,
      model: model,
      metrics: metrics,
      parameters: modelParams,
    });
    onClose();
  };

  return (
    <>
      <DialogContent>
        <Typography variant="h5" gutterBottom>
          Select Train Parameters
        </Typography>

        <Grid container>
          <Grid item xs={12}>
            <Typography variant="body1">Split Data:</Typography>
          </Grid>

          <Grid item xs={12} md={6} sx={{ pr: 2 }}>
            <TextField
              label="Input Columns"
              fullWidth
              value={inputColumns}
              onChange={(e) => setInputColumns(e.target.value)}
              margin="normal"
            />
            <TextField
              label="Output Columns"
              fullWidth
              value={outputColumns}
              onChange={(e) => setOutputColumns(e.target.value)}
              margin="normal"
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              label="Training (%)"
              type="number"
              fullWidth
              value={splits.train}
              onChange={(e) => setSplits({ ...splits, train: parseInt(e.target.value, 10) })}
              margin="normal"
            />
            <TextField
              label="Validation (%)"
              type="number"
              fullWidth
              value={splits.validation}
              onChange={(e) => setSplits({ ...splits, validation: parseInt(e.target.value, 10) })}
              margin="normal"
            />
            <TextField
              label="Testing (%)"
              type="number"
              fullWidth
              value={splits.test}
              onChange={(e) => setSplits({ ...splits, test: parseInt(e.target.value, 10) })}
              margin="normal"
            />
          </Grid>

          <Grid item xs={12} sx={{ mt: 2 }}>
            <Typography variant="body1">Task and Model:</Typography>
          </Grid>

          <Grid item xs={12}>
            <TextField
              label="Task"
              select
              fullWidth
              value={task}
              onChange={(e) => {
                setTask(e.target.value);
                setModel("");
                setMetrics([]);
              }}
              margin="normal"
            >
              {Object.keys(taskModelOptions).map((taskKey) => (
                <MenuItem key={taskKey} value={taskKey}>
                  {taskKey}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={12}>
            <Grid container spacing={1} alignItems="center">
              <Grid item xs>
                <TextField
                  label="Model"
                  select
                  fullWidth
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  margin="normal"
                  disabled={!task}
                >
                  {(taskModelOptions[task] || []).map((modelName) => (
                    <MenuItem key={modelName} value={modelName}>
                      {modelName}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid item>
                <IconButton
                  onClick={() => setOpenSettings(true)}
                  disabled={!model}
                  aria-label="model settings"
                  sx={{ mt: '8px' }}
                >
                  <SettingsIcon />
                </IconButton>
              </Grid>
            </Grid>
          </Grid>

          <Grid item xs={12} sx={{ mt: 2 }}>
            <Typography variant="body1">Metrics:</Typography>
          </Grid>

          <Grid item xs={12}>
            <TextField
              label="Metrics"
              select
              fullWidth
              SelectProps={{ multiple: true }}
              value={metrics}
              onChange={(e) => setMetrics(e.target.value)}
              margin="normal"
              disabled={!task}
            >
              {(availableMetrics[task] || []).map((metric) => (
                <MenuItem key={metric} value={metric}>
                  {metric}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>

        <Box mt={3}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={handleSave}
            disabled={
              loading ||
              inputColumns.length === 0 ||
              outputColumns.length === 0 ||
              splits.train + splits.validation + splits.test !== 100 ||
              !task ||
              !model ||
              metrics.length === 0
            }
          >
            Save
          </Button>
        </Box>
      </DialogContent>

      <ParamsSettings
        open={openSettings}
        modelSchema={modelSchema}
        values={modelParams}
        onChange={handleChange}
        onClose={() => setOpenSettings(false)}
      />

    </>
  );
};

export default Train;
