import React from "react";
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
} from "@mui/material";
import { styled } from "@mui/material/styles";

const LabelTypography = styled(Typography)(({ theme }) => ({
  fontWeight: "bold",
  color: theme.palette.text.secondary,
}));

const ValueTypography = styled(Typography)(({ theme }) => ({
  fontFamily: theme.typography.fontFamily,
  wordBreak: "break-word",
}));

const CodePaper = styled(Paper)(({ theme }) => ({
  backgroundColor:
    theme.palette.mode === "dark"
      ? theme.palette.grey[900]
      : theme.palette.grey[100],
  padding: theme.spacing(2),
  fontFamily: "monospace",
  fontSize: "0.875rem",
  overflow: "auto",
  maxHeight: "200px",
}));

const JobDetailsDialog = ({ job, open, onClose }) => {
  if (!job) return null;

  // Format timestamp for display
  const formatTime = (timestamp) => {
    if (!timestamp) return "N/A";

    try {
      const date = new Date(timestamp.replace(" ", "T"));
      return new Intl.DateTimeFormat("en-US", {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZoneName: "short",
      }).format(date);
    } catch (e) {
      return timestamp;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Job Details
        <Chip
          label={job.status}
          color={
            job.status === "finished"
              ? "success"
              : job.status === "error"
              ? "error"
              : job.status === "started"
              ? "primary"
              : job.status === "deleted"
              ? "warning"
              : "default"
          }
          size="small"
          sx={{ ml: 1 }}
        />
      </DialogTitle>

      <DialogContent>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <LabelTypography variant="subtitle2">Job ID</LabelTypography>
            <ValueTypography variant="body1" sx={{ fontFamily: "monospace" }}>
              {job.id}
            </ValueTypography>
          </Grid>

          <Grid item xs={12} md={6}>
            <LabelTypography variant="subtitle2">Task Type</LabelTypography>
            <ValueTypography variant="body1">{job.task_type}</ValueTypography>
          </Grid>

          <Grid item xs={12} md={6}>
            <LabelTypography variant="subtitle2">Last Updated</LabelTypography>
            <ValueTypography variant="body1">
              {formatTime(job.last_update)}
            </ValueTypography>
          </Grid>

          <Grid item xs={12} md={6}>
            <LabelTypography variant="subtitle2">Enqueued At</LabelTypography>
            <ValueTypography variant="body1">
              {formatTime(job.enqueued_at)}
            </ValueTypography>
          </Grid>

          <Grid item xs={12} md={6}>
            <LabelTypography variant="subtitle2">Status</LabelTypography>
            <ValueTypography variant="body1">{job.status}</ValueTypography>
          </Grid>

          {job.error_msg && (
            <Grid item xs={12}>
              <Box mt={2}>
                <Divider />
                <LabelTypography
                  variant="subtitle2"
                  color="error"
                  sx={{ mt: 2 }}
                >
                  Error Message
                </LabelTypography>
                <CodePaper variant="outlined">{job.error_msg}</CodePaper>
              </Box>
            </Grid>
          )}
        </Grid>
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
