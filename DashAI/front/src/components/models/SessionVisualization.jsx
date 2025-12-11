import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { Box, Typography, Stack, Paper } from "@mui/material";
import JobQueueWidget from "../jobs/JobQueueWidget";
import ModelComparisonTable from "./ModelComparisonTable";
import RunCard from "./RunCard";
import { getComponents } from "../../api/component";

export default function SessionVisualization({
  session,
  runs = [],
  onTrain,
  onEditRun,
  onRetryRun,
  onDeleteRun,
}) {
  const [models, setModels] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await getComponents({ selectTypes: ["Model"] });
        setModels(response);
      } catch (error) {
        console.error("Error fetching models:", error);
      }
    };
    fetchModels();
  }, []);

  const handleRowClick = (runId) => {
    setSelectedRunId(runId);
    // Scroll to the run card
    const element = document.getElementById(`run-card-${runId}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  const handleViewDetails = (run) => {
    setSelectedRunId(run.id);
    const element = document.getElementById(`run-card-${run.id}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  // Sort runs in ascending order (oldest first, newest last)
  const sortedRuns = [...runs].sort(
    (a, b) => new Date(a.created) - new Date(b.created),
  );

  if (!session) {
    return (
      <>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
            justifyContent: "center",
            alignItems: "center",
            p: 4,
          }}
        >
          <Typography variant="h5" color="text.secondary">
            No Session Selected
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
            Select a session from the left panel to begin
          </Typography>
        </Box>
        <JobQueueWidget />
      </>
    );
  }

  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "hidden",
        }}
      >
        {/* Sticky Comparison Table */}
        <Paper
          elevation={0}
          sx={{
            height: 280,
            flexShrink: 0,
            borderBottom: "1px solid",
            borderColor: "divider",
            p: 2,
          }}
        >
          <Typography variant="h6" sx={{ mb: 2 }}>
            Model Comparison
          </Typography>
          {runs.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "calc(100% - 40px)",
              }}
            >
              <Typography variant="body2" color="text.secondary">
                No runs yet. Add models from the right panel.
              </Typography>
            </Box>
          ) : (
            <Box sx={{ height: "calc(100% - 40px)" }}>
              <ModelComparisonTable
                runs={runs}
                session={session}
                onTrain={onTrain}
                onViewDetails={handleViewDetails}
                onDelete={onDeleteRun}
                onRowClick={handleRowClick}
              />
            </Box>
          )}
        </Paper>

        {/* Scrollable Run Cards */}
        <Box
          sx={{
            flex: 1,
            overflow: "auto",
            p: 2,
          }}
        >
          {runs.length === 0 ? (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
              }}
            >
              <Typography variant="body1" color="text.secondary">
                No runs in this session. Click a model in the right panel to add
                one.
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2}>
              {sortedRuns.map((run) => (
                <Box
                  key={run.id}
                  id={`run-card-${run.id}`}
                  sx={{
                    scrollMarginTop: "20px",
                    transition: "all 0.3s ease",
                    ...(selectedRunId === run.id && {
                      transform: "scale(1.02)",
                      boxShadow: 3,
                    }),
                  }}
                >
                  <RunCard
                    run={run}
                    models={models}
                    onTrain={onTrain}
                    onEdit={onEditRun}
                    onRetry={onRetryRun}
                    onDelete={onDeleteRun}
                  />
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Box>
      <JobQueueWidget />
    </>
  );
}

SessionVisualization.propTypes = {
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  runs: PropTypes.array,
  onTrain: PropTypes.func.isRequired,
  onEditRun: PropTypes.func.isRequired,
  onRetryRun: PropTypes.func.isRequired,
  onDeleteRun: PropTypes.func.isRequired,
};
