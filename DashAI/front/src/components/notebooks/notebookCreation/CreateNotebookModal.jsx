import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  TextField,
  Box,
  Typography,
  IconButton,
  Chip,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import { getDatasetInfo } from "../../../api/datasets";
import { formatDate } from "../../../pages/results/constants/formatDate";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import DatasetNoteBox from "../notebook/DatasetNoteBox";

export function CreateNotebookModal({
  open,
  onClose,
  onCreateNotebook,
  dataset,
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [infoError, setInfoError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const fetchInfo = async () => {
      if (!dataset?.id) {
        setDatasetInfo(null);
        setInfoError(null);
        return;
      }
      try {
        setLoadingInfo(true);
        setInfoError(null);
        const info = await getDatasetInfo(dataset.id);
        if (!cancelled) setDatasetInfo(info);
      } catch (e) {
        if (!cancelled) setInfoError("Failed to load dataset info");
      } finally {
        if (!cancelled) setLoadingInfo(false);
      }
    };
    fetchInfo();
    return () => {
      cancelled = true;
    };
  }, [dataset?.id]);

  const handleSubmit = () => {
    onCreateNotebook({
      name: name.trim() || "Untitled Notebook",
      description: description.trim() || "",
    });
    handleClose();
  };

  const handleClose = () => {
    setName("");
    setDescription("");
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Create a New Notebook
        <IconButton
          onClick={handleClose}
          sx={{ position: "absolute", right: 8, top: 8 }}
        >
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          <DatasetNoteBox />
          {/* Selected Dataset Info Box */}
          {dataset && (
            <Box
              sx={{
                p: 3,
                border: 1,
                borderColor: "divider",
                borderRadius: 2,
                mb: 2,
              }}
            >
              <Typography variant="h6" gutterBottom>
                Selected Dataset
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="body2" fontWeight="medium">
                    Name:
                  </Typography>
                  <Chip label={dataset.name} size="small" />
                </Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="body2" fontWeight="medium">
                    Created:
                  </Typography>
                  <Typography variant="body2">
                    {formatDate(dataset.created)}
                  </Typography>
                </Box>
                <Typography variant="body2" fontWeight="medium">
                  Rows:{" "}
                  {loadingInfo ? "Loading..." : datasetInfo?.total_rows ?? "-"}{" "}
                  | Columns:{" "}
                  {loadingInfo
                    ? "Loading..."
                    : datasetInfo?.total_columns ?? "-"}
                </Typography>
                {infoError && (
                  <Typography variant="caption" color="error">
                    {infoError}
                  </Typography>
                )}
              </Box>
            </Box>
          )}
          <Typography
            variant="h6"
            sx={{
              whiteSpace: "normal",
              wordBreak: "break-word",
              my: 2,
            }}
          >
            Name your Notebook
          </Typography>
          {/* Notebook name */}
          <TextField
            fullWidth
            label="Notebook Name"
            name="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            variant="outlined"
            placeholder="Enter a name for your notebook (optional)"
            sx={{ mb: 2 }}
          />
          {/* Notebook description */}
          <TextField
            fullWidth
            label="Notebook Description"
            name="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            variant="outlined"
            placeholder="Describe what this notebook will be used for (optional)"
            sx={{ mb: 2 }}
          />
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
            <FormSchemaButtonGroup
              onCancel={handleClose}
              onFormSubmit={handleSubmit}
              formik={{ errors: {} }} // No validation errors for this modal
              saveButtonText="Create Notebook"
              backButtonText="Cancel"
            />
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
