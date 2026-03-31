import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Grid,
  Chip,
  Paper,
  Box,
  Divider,
  CircularProgress,
} from "@mui/material";
import { getJobDetails } from "../../api/job";
import { formatDate } from "../../utils";

const JobDetailsDialog = ({ job, open, onClose }) => {
  const [state, setState] = useState({
    jobDetails: null,
    loading: false,
  });

  useEffect(() => {
    if (job && job.id && open) {
      setState({ jobDetails: job, loading: true });

      const fetchDetails = async () => {
        try {
          const data = await getJobDetails(job.id);
          setState({ jobDetails: { ...job, ...data }, loading: false });
        } catch (error) {
          console.error("Error fetching job details:", error);
          setState({ jobDetails: job, loading: false });
        }
      };

      fetchDetails();
    } else {
      setState({ jobDetails: job, loading: false });
    }
  }, [job?.id, open]);

  if (!job) return null;

  const { jobDetails, loading } = state;
  const displayJob = jobDetails || job;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Job Details
        <Chip
          label={displayJob.status}
          color={
            displayJob.status === "finished"
              ? "success"
              : displayJob.status === "error"
                ? "error"
                : displayJob.status === "started"
                  ? "primary"
                  : displayJob.status === "deleted"
                    ? "warning"
                    : "default"
          }
          size="small"
          sx={{ ml: 1 }}
        />
      </DialogTitle>

      <DialogContent>
        {loading ? (
          <Box display="flex" justifyContent="center" my={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: "bold", color: "text.secondary" }}
              >
                Job ID
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  wordBreak: "break-word",
                  fontFamily: (theme) => theme.typography.fontFamily,
                }}
              >
                {displayJob.entity_id || "N/A"}
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: "bold", color: "text.secondary" }}
              >
                Job Name
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  fontFamily: (theme) => theme.typography.fontFamily,
                  wordBreak: "break-word",
                }}
              >
                {displayJob.job_name || "Unnamed Job"}
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: "bold", color: "text.secondary" }}
              >
                Job Type
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  fontFamily: (theme) => theme.typography.fontFamily,
                  wordBreak: "break-word",
                }}
              >
                {displayJob.entity_type ||
                  (displayJob.task_type
                    ? displayJob.task_type.split(".").pop()
                    : "Unknown")}
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: "bold", color: "text.secondary" }}
              >
                Last Updated
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  fontFamily: (theme) => theme.typography.fontFamily,
                  wordBreak: "break-word",
                }}
              >
                {formatDate(displayJob.last_modified || displayJob.last_update)}
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: "bold", color: "text.secondary" }}
              >
                Created At
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  fontFamily: (theme) => theme.typography.fontFamily,
                  wordBreak: "break-word",
                }}
              >
                {formatDate(displayJob.created_at || displayJob.enqueued_at)}
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Typography
                variant="subtitle2"
                sx={{ fontWeight: "bold", color: "text.secondary" }}
              >
                Status
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  fontFamily: (theme) => theme.typography.fontFamily,
                  wordBreak: "break-word",
                }}
              >
                {displayJob.status}
              </Typography>
            </Grid>

            {displayJob.error_msg && (
              <Grid size={{ xs: 12 }}>
                <Box mt={2}>
                  <Divider />
                  <Typography
                    variant="subtitle2"
                    sx={{ fontWeight: "bold", color: "error.main", mt: 2 }}
                  >
                    Error Message
                  </Typography>
                  <Paper
                    variant="outlined"
                    sx={{
                      backgroundColor: (theme) =>
                        theme.palette.mode === "dark"
                          ? theme.palette.grey[900]
                          : theme.palette.grey[100],
                      p: 2,
                      fontSize: "0.875rem",
                      overflow: "auto",
                      maxHeight: "200px",
                    }}
                  >
                    {displayJob.error_msg}
                  </Paper>
                </Box>
              </Grid>
            )}
          </Grid>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} color="primary">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default JobDetailsDialog;
