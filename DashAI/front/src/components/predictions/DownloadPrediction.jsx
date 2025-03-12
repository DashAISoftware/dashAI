import React, { useEffect, useState } from "react";
import { Download, FileDownload } from "@mui/icons-material";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { download_predict as downloadPredictionRequest } from "../../api/predict";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Typography,
  Tabs,
  Tab,
} from "@mui/material";

function DownloadPrediction({ predictName }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [json, setJson] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const downloadPrediction = async (predict_name) => {
    setLoading(true);
    try {
      const json = await downloadPredictionRequest(predict_name);
      setJson(json);
      const blob = new Blob([JSON.stringify(json, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = predict_name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      enqueueSnackbar("Error when trying to download the prediction");
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = () => {
    setOpen(true);
    downloadPrediction(predictName);
  };

  return (
    <>
      <GridActionsCellItem
        key="prediction-summary-button"
        icon={<Download />}
        label="Prediction Summary"
        onClick={handleOpen}
        sx={{ color: "info.dark" }}
      />
    </>
  );
}

export default DownloadPrediction;
