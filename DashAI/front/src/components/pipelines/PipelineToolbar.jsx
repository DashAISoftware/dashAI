import React from "react";
import { Box, TextField, Button, IconButton, Tooltip } from "@mui/material";
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
        <Button variant="contained" color="primary" onClick={onRun}>
          Run
        </Button>
      </Box>
    </Box>
  );
}

export default PipelineToolbar;
