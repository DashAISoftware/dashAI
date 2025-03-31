import React, { useEffect, useState } from "react";
import { Search } from "@mui/icons-material";
import { GridActionsCellItem } from "@mui/x-data-grid";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Typography,
  Tabs,
  Tab,
} from "@mui/material";
import { useSnackbar } from "notistack";
import PredictionSummaryTab from "./PredictionSummaryTab";
import PredictionSampleTab from "./PredictionSampleTab";
import { get_predict_summary as getPredictSummaryRequest } from "../../api/predict";

function PredictionSummaryModal({ predictName }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const { enqueueSnackbar } = useSnackbar();
  const [error, setError] = useState(false);

  const handleCloseContent = () => {
    setOpen(false);
  };
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };
  const [summary, setSummary] = useState({});

  const getPredictSummary = async () => {
    setLoading(true);
    try {
      const summary = await getPredictSummaryRequest(predictName);
      setSummary(summary);
      if (summary.data_type === "string") {
        setActiveTab(1);
      }
    } catch (error) {
      enqueueSnackbar("Error when trying to get the prediction summary");
      setError(true);
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
    getPredictSummary();
  };

  return (
    <>
      <GridActionsCellItem
        key="prediction-summary-button"
        icon={<Search />}
        label="Prediction Summary"
        onClick={handleOpen}
        sx={{ color: "warning.main" }}
      />
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        fullWidth
        maxWidth={"md"}
      >
        <DialogTitle>
          <Grid container direction="row" justifyContent="space-between">
            <Typography variant="h5" component="h2">
              Prediction Summary
            </Typography>
          </Grid>
        </DialogTitle>
        <DialogContent>
          <Grid
            container
            direction="row"
            alignItems="stretch"
            spacing={2}
            onClick={(event) => event.stopPropagation()}
          >
            <Grid item xs={12}>
              {summary.data_type !== "string" && (
                <Tabs
                  value={activeTab}
                  onChange={handleTabChange}
                  aria-label="Prediction Tabs"
                  centered
                  sx={{ mb: 3 }}
                >
                  <Tab label="Summary" />
                  <Tab label="Sample" />
                </Tabs>
              )}
              {summary.data_type === "string" ? (
                <PredictionSampleTab summary={summary} />
              ) : (
                <>
                  {activeTab === 0 && (
                    <PredictionSummaryTab summary={summary} />
                  )}
                  {activeTab === 1 && (
                    <PredictionSampleTab summary={summary} type={"numeric"} />
                  )}
                </>
              )}
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default PredictionSummaryModal;
