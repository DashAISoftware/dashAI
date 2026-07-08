import React from "react";
import {
  Box,
  TextField,
  Button,
  IconButton,
  Tooltip,
  CircularProgress,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import LightModeIcon from "@mui/icons-material/LightMode";
import DarkModeIcon from "@mui/icons-material/DarkMode";

function PipelineToolbar({
  pipelineName,
  setPipelineName,
  onRun,
  nameError,
  nameErrorMessage,
  handlePipelineNameChange,
  canvasMode,
  setCanvasMode,
  isRunning = false,
}) {
  const theme = useTheme();

  const toggleCanvasMode = () => {
    setCanvasMode((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        mb: 2,
        p: 1.5,
        borderRadius: 2,
        backgroundColor: theme.palette.background.box,
        border: `1px solid ${theme.palette.ui.borderLight}`,
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
          mr: 2,
          input: { color: theme.palette.text.primary },
          "& .MuiOutlinedInput-root fieldset": {
            borderColor: theme.palette.ui.border,
          },
          "& label": { color: theme.palette.text.secondary },
        }}
      />
      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
        <Tooltip
          title={
            canvasMode === "dark"
              ? "Switch to light canvas"
              : "Switch to dark canvas"
          }
        >
          <IconButton onClick={toggleCanvasMode} size="small">
            {canvasMode === "dark" ? (
              <LightModeIcon
                sx={{ color: theme.palette.text.primary, fontSize: 22 }}
              />
            ) : (
              <DarkModeIcon
                sx={{ color: theme.palette.text.primary, fontSize: 22 }}
              />
            )}
          </IconButton>
        </Tooltip>
        <Button
          variant="contained"
          color="primary"
          onClick={onRun}
          disabled={isRunning}
          startIcon={
            isRunning ? (
              <CircularProgress size={16} color="inherit" />
            ) : undefined
          }
        >
          {isRunning ? "Running..." : "Run"}
        </Button>
      </Box>
    </Box>
  );
}

export default PipelineToolbar;
