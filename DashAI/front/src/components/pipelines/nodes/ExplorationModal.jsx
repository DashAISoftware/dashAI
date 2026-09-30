import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  ButtonGroup,
  IconButton,
  useMediaQuery,
  useTheme,
  Box,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ConfigureExplorersStep from "../../../components/explorations/Steps/ConfigureExplorersStep";
import { useExplorationsContext } from "../../../components/explorations/context";
import { validateNode } from "../../../api/pipeline";
import { useSnackbar } from "notistack";

function ConfigureExplorersModal({
  open,
  onClose,
  onSave,
  savedConfig,
  displayMode = "dialog",
}) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const [valid, setValid] = useState(false);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();

  const {
    explorationData,
    setExplorerData,
    datasetColumns,
    setExplorationData,
  } = useExplorationsContext();

  useEffect(() => {
    if (datasetColumns && datasetColumns.length > 0) {
      if (savedConfig?.explorations?.length > 0) {
        const transformedExplorers = savedConfig.explorations.map(
          (explorer) => {
            return {
              exploration_type: explorer.exploration_type,
              parameters: explorer.parameters,
              columns: explorer.columns,
              id: explorer.id,
              name: explorer.name,
            };
          },
        );
        setExplorationData((prev) => ({
          ...prev,
          explorers: transformedExplorers,
        }));
      } else {
        setExplorerData((prev) => ({ ...prev }));
      }
      setLoading(false);
    } else {
      setLoading(true);
    }
  }, [datasetColumns, setExplorerData, savedConfig]);

  const handleSave = async () => {
    const config = {
      explorations: explorationData.explorers.map((explorer, index) => ({
        exploration_type: explorer.exploration_type,
        parameters: explorer.parameters,
        columns: explorer.columns,
        id: index,
        name: explorer.name,
      })),
    };

    try {
      const response = await validateNode("DataExploration", config);
      if (response.status === "ok") {
        onSave(config);
        onClose();
      } else {
        enqueueSnackbar("Validation failed", { variant: "error" });
      }
    } catch (e) {
      enqueueSnackbar("Error validating node", { variant: "error" });
      console.error(e);
    }
  };

  if (!open) {
    return null;
  }

  if (loading) {
    return null;
  }

  if (displayMode === "panel") {
    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Typography variant="subtitle1">Configure Explorers</Typography>
        <Box mt={1}>
          <ConfigureExplorersStep onValidation={setValid} />
        </Box>
        <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={!valid}
            color="primary"
          >
            Save
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <Dialog
      open={open}
      onClose={() => {}}
      disableEscapeKeyDown
      fullScreen={fullScreen}
      maxWidth="lg"
      fullWidth
      slotProps={{
        paper: {
          sx: { minHeight: "80vh" },
        },
      }}
    >
      <DialogTitle>
        Configure Explorers
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{
            position: "absolute",
            right: 8,
            top: 8,
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Box mt={4}>
          <ConfigureExplorersStep onValidation={setValid} />
        </Box>
      </DialogContent>
      <DialogActions>
        <ButtonGroup size="large">
          <Button onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={!valid}
            autoFocus
            color="primary"
          >
            Save
          </Button>
        </ButtonGroup>
      </DialogActions>
    </Dialog>
  );
}

export default ConfigureExplorersModal;
