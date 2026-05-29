import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  CircularProgress,
} from "@mui/material";
import { useSnackbar } from "notistack";
import { getPipelinePredictionSummary } from "../../../api/pipeline";

function PredictionSummary({ predictName }) {
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);
  const [summary, setSummary] = useState({});
  const { enqueueSnackbar } = useSnackbar();

  const handleTabChange = (_, newValue) => {
    setTab(newValue);
  };

  const getPredictSummary = async () => {
    setLoading(true);
    try {
      const res = await getPipelinePredictionSummary(predictName);
      setSummary(res);
      if (res.data_type === "string") {
        setTab(2);
      }
    } catch (error) {
      enqueueSnackbar("Error when trying to get the prediction summary");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getPredictSummary();
  }, [predictName]);

  if (loading) {
    return <CircularProgress size={24} />;
  }

  return (
    <Box my={2}>
      <Paper sx={{ width: "100%" }}>
        <Tabs value={tab} onChange={handleTabChange} variant="scrollable">
          <Tab label="Info" />
          <Tab label="Summary" disabled={summary.data_type === "string"} />
          <Tab label="Sample" />
        </Tabs>
        <Box sx={{ p: 6 }}>
          {tab === 0 && (
            <Box>
              <Typography variant="subtitle1">Name</Typography>
              <Typography variant="p" sx={{ color: "gray" }}>
                {predictName ?? "-"}
              </Typography>
            </Box>
          )}
          {tab === 1 && summary.data_type !== "string" && (
            <>Prediction Summary Tab Placeholder</>
          )}
          {tab === 2 && <>Prediction Sample Table Placeholder</>}
        </Box>
      </Paper>
    </Box>
  );
}

export default PredictionSummary;
