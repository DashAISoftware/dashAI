import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  Grid,
  Typography,
  Tabs,
  Tab,
  IconButton
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useSnackbar } from "notistack";
import PredictionSummaryTab from "../../components/predictions/PredictionSummaryTab";
import PredictionSampleTab from "../../components/predictions/PredictionSampleTab";
import { get_pipeline_prediction_summary as getPipelinePredictionSummary } from "../../api/pipeline";

function PredictionSummaryModal({ predictName, open, onClose }) {
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState(0);
    const { enqueueSnackbar } = useSnackbar();
    const [error, setError] = useState(false);
    const [summary, setSummary] = useState({});
  
    const handleTabChange = (event, newValue) => {
      setActiveTab(newValue);
    };
  
    const getPredictSummary = async () => {
      setLoading(true);
      try {
        const summary = await getPipelinePredictionSummary(predictName);
        setSummary(summary);
        if (summary.data_type === "string") {
          setActiveTab(1);
        }
      } catch (error) {
        enqueueSnackbar("Error when trying to get the prediction summary");
        setError(true);
        console.error("Error:", error);
      } finally {
        setLoading(false);
      }
    };
  
    useEffect(() => {
      if (open) {
        getPredictSummary();
      }
    }, [open]);
  
    return (
      <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
        <DialogTitle>
          <Grid container justifyContent="space-between">
            <Typography variant="h5">Prediction Summary</Typography>
            <IconButton
              aria-label="close"
              onClick={onClose}
              sx={{
                color: (theme) => theme.palette.grey[500],
              }}
            >
              <CloseIcon />
            </IconButton>
          </Grid>
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} onClick={(e) => e.stopPropagation()}>
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
                  {activeTab === 0 && <PredictionSummaryTab summary={summary} />}
                  {activeTab === 1 && (
                    <PredictionSampleTab summary={summary} type="numeric" />
                  )}
                </>
              )}
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    );
  }

export default PredictionSummaryModal;
  