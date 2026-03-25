import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Paper,
  Typography,
  IconButton,
  Badge,
  Collapse,
  List,
  CircularProgress,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Tooltip,
  Fade,
  Divider,
  Chip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { deleteJob } from "../../api/job";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import DeleteIcon from "@mui/icons-material/Delete";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import RefreshIcon from "@mui/icons-material/Refresh";
import JobDetailsDialog from "./JobDetailsDialog";
import DeleteSweepIcon from "@mui/icons-material/DeleteSweep";
import { deleteAllJobs } from "../../api/job";
import { useJobManager } from "../../hooks/useJobPolling";

export const StatusIcon = ({ status }) => {
  switch (status) {
    case "not_started":
      return <HourglassEmptyIcon fontSize="small" />;
    case "started":
      return <PlayArrowIcon fontSize="small" color="primary" />;
    case "finished":
      return <CheckCircleIcon fontSize="small" color="success" />;
    case "error":
      return <ErrorIcon fontSize="small" color="error" />;
    case "deleted":
      return <DeleteIcon fontSize="small" />;
    default:
      return <MoreHorizIcon fontSize="small" />;
  }
};

export const statusText = {
  not_started: "Queued",
  started: "Running",
  finished: "Completed",
  error: "Failed",
  deleted: "Deleted",
};

const JobQueueWidget = () => {
  const [expanded, setExpanded] = useState(() => {
    try {
      const savedState = localStorage.getItem("jobQueueWidgetExpanded");
      return savedState === "true";
    } catch (e) {
      return false;
    }
  });
  const [selectedJob, setSelectedJob] = useState(null);
  const [showFinished, setShowFinished] = useState(false);
  const [jobToDelete, setJobToDelete] = useState(null);
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [clearingAll, setClearingAll] = useState(false);
  const [forceUpdate, setForceUpdate] = useState(0);
  const [isHovered, setIsHovered] = useState(false);

  const handleClearAllJobs = () => {
    setConfirmClearAll(true);
  };

  const confirmClearAllJobs = async () => {
    try {
      setClearingAll(true);
      await deleteAllJobs();
      refresh();
      setTimeout(() => {
        refresh();
        setClearingAll(false);
        setConfirmClearAll(false);
      }, 500);
    } catch (error) {
      console.error("Error clearing all jobs:", error);
      setClearingAll(false);
      setConfirmClearAll(false);
    }
  };

  const cancelClearAllJobs = () => {
    setConfirmClearAll(false);
  };

  const handleDeleteJob = (job) => {
    setJobToDelete(job);
  };

  const confirmDeleteJob = async () => {
    if (!jobToDelete) return;

    try {
      await deleteJob(jobToDelete.id);

      setTimeout(() => {
        refresh();
      }, 500);
    } catch (error) {
      console.error("Error deleting job:", error);
    } finally {
      setJobToDelete(null);
    }
  };

  const cancelDeleteJob = () => {
    setJobToDelete(null);
  };

  const { jobs, loading, error, refresh } = useJobManager();

  const activeJobs = jobs.filter(
    (job) => job.status === "started" || job.status === "not_started",
  );
  const finishedJobs = jobs.filter((job) => job.status === "finished");
  const errorJobs = jobs.filter((job) => job.status === "error");

  const hasInitializedRef = useRef(false);
  const prevActiveCountRef = useRef(0);

  // Snapshot del estado inicial al completar la primera carga (evita tratar
  // jobs ya existentes como nuevos y disparar el expand al montar)
  useEffect(() => {
    if (!loading && !hasInitializedRef.current) {
      hasInitializedRef.current = true;
      prevActiveCountRef.current = activeJobs.length;
    }
  }, [loading, activeJobs.length]);

  // Auto expand/collapse por transiciones reales durante la sesión
  useEffect(() => {
    if (!hasInitializedRef.current) return;
    const prev = prevActiveCountRef.current;
    const curr = activeJobs.length;
    if (prev === 0 && curr > 0) {
      setExpanded(true);
    } else if (prev > 0 && curr === 0) {
      setExpanded(false);
    }
    prevActiveCountRef.current = curr;
  }, [activeJobs.length]);

  useEffect(() => {
    try {
      localStorage.setItem("jobQueueWidgetExpanded", String(expanded));
    } catch (e) {
      // ignore
    }
  }, [expanded]);

  const handleToggleExpand = () => {
    setExpanded(!expanded);
  };

  const handleJobClick = (job) => {
    setSelectedJob(job);
  };

  const handleCloseDetails = () => {
    setSelectedJob(null);
  };

  const handleRefresh = () => {
    setForceUpdate((prev) => prev + 1);
    refresh();
  };

  const getJobsToShow = () => {
    if (showFinished) {
      return jobs;
    } else {
      return [...activeJobs]
        .sort((a, b) => new Date(b.last_update) - new Date(a.last_update))
        .slice(0, 10);
    }
  };

  const getRelativeTime = useCallback(
    (timestamp) => {
      try {
        const date = timestamp.includes("T")
          ? new Date(timestamp)
          : new Date(timestamp.replace(" ", "T") + "Z");

        const now = new Date();

        const diffSeconds = Math.floor((now - date) / 1000);

        if (diffSeconds < 0) {
          if (diffSeconds > -60) return "just now";

          const absDiff = Math.abs(diffSeconds);
          if (absDiff < 60) return `in ${absDiff}s`;
          if (absDiff < 3600) return `in ${Math.floor(absDiff / 60)}m`;
          if (absDiff < 86400) return `in ${Math.floor(absDiff / 3600)}h`;
          return `in ${Math.floor(absDiff / 86400)}d`;
        }

        if (diffSeconds < 30) return "just now";
        if (diffSeconds < 60) return `${diffSeconds}s ago`;
        if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
        if (diffSeconds < 86400)
          return `${Math.floor(diffSeconds / 3600)}h ago`;
        return `${Math.floor(diffSeconds / 86400)}d ago`;
      } catch (e) {
        console.error("Error parsing time:", e, timestamp);
        return "time unknown";
      }
    },
    [forceUpdate],
  );

  const jobsToShow = getJobsToShow();
  //filter: `brightness(${isHovered || expanded ? 1 : 0.7})`,
  return (
    <>
      <Fade in={true}>
        <Paper
          elevation={6}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          sx={{
            position: "fixed",
            bottom: { xs: 16, sm: (theme) => theme.spacing(3) },
            right: { xs: 16, sm: (theme) => theme.spacing(3) },
            zIndex: 1000,
            width: { xs: "calc(100vw - 32px)", sm: 320 },
            maxWidth: 320,
            maxHeight: { xs: "60vh", sm: "80vh" },
            display: "flex",
            flexDirection: "column",
            boxShadow: (theme) => theme.shadows[6],
            borderRadius: (theme) => theme.shape.borderRadius,
            overflow: "hidden",
          }}
          style={{
            opacity: `${isHovered || expanded ? 1 : 0.5}`,
            filter: `brightness(${isHovered || expanded ? 1 : 0.5})`,
            transition: "all 0.2s ease",
          }}
        >
          <Box
            onClick={handleToggleExpand}
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: (theme) => theme.spacing(1, 2),
              backgroundColor: (theme) => theme.palette.primary.main,
              color: (theme) => theme.palette.primary.contrastText,
              cursor: "pointer",
            }}
          >
            <Box display="flex" alignItems="center">
              <Badge
                badgeContent={activeJobs.length}
                color="error"
                sx={{ mr: 1.5 }}
              >
                <TaskAltIcon />
              </Badge>
              <Typography variant="subtitle1" sx={{ fontWeight: "medium" }}>
                Job Queue
              </Typography>
            </Box>
            <Box display="flex" alignItems="center">
              {jobs.length > 0 && (
                <Tooltip title="Clear All Jobs">
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleClearAllJobs();
                    }}
                    sx={{ color: "white", opacity: 0.8, mr: 0.5 }}
                  >
                    <DeleteSweepIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              <Tooltip title="Refresh">
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRefresh();
                  }}
                  sx={{ color: "white", opacity: 0.8, mr: 0.5 }}
                >
                  <RefreshIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              {expanded ? (
                <KeyboardArrowDownIcon fontSize="small" />
              ) : (
                <KeyboardArrowUpIcon fontSize="small" />
              )}
            </Box>
          </Box>

          <Collapse in={expanded} timeout="auto">
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                backgroundColor: (theme) => theme.palette.background.paper,
              }}
            >
              <Box
                sx={{
                  maxHeight: { xs: 180, sm: 280 },
                  overflowY: "auto",
                }}
              >
                {loading && jobs.length === 0 && (
                  <Box display="flex" justifyContent="center" p={2}>
                    <Typography variant="body2" color="text.secondary">
                      Loading jobs...
                    </Typography>
                  </Box>
                )}

                {error && (
                  <Box p={2}>
                    <Typography variant="body2" color="error">
                      Error: {error}
                    </Typography>
                  </Box>
                )}

                {jobs.length === 0 && !loading && (
                  <Box display="flex" justifyContent="center" p={2}>
                    <Typography variant="body2" color="text.secondary">
                      No jobs in queue
                    </Typography>
                  </Box>
                )}

                {jobsToShow.length > 0 && (
                  <List dense disablePadding>
                    {jobsToShow.map((job) => (
                      <ListItem
                        key={job.id}
                        component="button"
                        divider
                        onClick={() => handleJobClick(job)}
                        sx={{
                          backgroundColor:
                            job.status === "started"
                              ? "rgba(25, 118, 210, 0.08)"
                              : undefined,
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 40 }}>
                          <StatusIcon status={job.status} />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center">
                              <Tooltip title={job.job_name || ""}>
                                <Typography variant="body2" noWrap>
                                  {job.job_name
                                    ? job.job_name
                                    : job.task_type
                                      ? job.task_type.split(".").pop()
                                      : "Unknown Job"}
                                </Typography>
                              </Tooltip>
                            </Box>
                          }
                          secondary={
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ display: "flex", alignItems: "center" }}
                            >
                              <span>
                                {statusText[job.status] || job.status}
                              </span>
                              {job.status === "error" && (
                                <Tooltip
                                  title={job.error_msg || "Unknown error"}
                                >
                                  <ErrorIcon
                                    fontSize="inherit"
                                    color="error"
                                    sx={{ ml: 0.5, fontSize: "1rem" }}
                                  />
                                </Tooltip>
                              )}
                            </Typography>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Box display="flex" alignItems="center">
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{ mr: 1 }}
                            >
                              {getRelativeTime(job.last_update)}
                            </Typography>
                            {(job.status === "not_started" ||
                              job.status === "error" ||
                              job.status === "finished") && (
                              <Tooltip title="Cancel job">
                                <IconButton
                                  edge="end"
                                  aria-label="delete"
                                  size="small"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteJob(job);
                                  }}
                                  sx={{ opacity: 0.7 }}
                                >
                                  <CloseIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )}
              </Box>

              {/* Panel fijo para los controles */}
              {jobs.length > 0 && (
                <>
                  <Divider />
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                    p={1}
                    sx={{
                      borderTop: "1px solid",
                      borderTopColor: "divider",
                    }}
                  >
                    <Box display="flex" gap={0.5}>
                      <Chip
                        label={`${activeJobs.length} active`}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                      <Chip
                        label={`${errorJobs.length} failed`}
                        size="small"
                        color="error"
                        variant="outlined"
                      />
                    </Box>

                    <Chip
                      label={showFinished ? "Hide Completed" : "Show Completed"}
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowFinished(!showFinished);
                      }}
                      clickable
                    />
                  </Box>
                </>
              )}
            </Box>
          </Collapse>
        </Paper>
      </Fade>

      <JobDetailsDialog
        job={selectedJob}
        open={Boolean(selectedJob)}
        onClose={handleCloseDetails}
      />

      <Dialog
        open={Boolean(jobToDelete)}
        onClose={cancelDeleteJob}
        aria-labelledby="delete-job-dialog-title"
      >
        <DialogTitle id="delete-job-dialog-title">Delete Job</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this job?
            {jobToDelete && (
              <Box component="span" fontWeight="bold" display="block" mt={1}>
                {jobToDelete.job_name || jobToDelete.task_type || "Unknown Job"}
              </Box>
            )}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={cancelDeleteJob} color="primary">
            Cancel
          </Button>
          <Button onClick={confirmDeleteJob} color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={confirmClearAll}
        onClose={cancelClearAllJobs}
        aria-labelledby="clear-all-dialog-title"
      >
        <DialogTitle id="clear-all-dialog-title">Clear All Jobs</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete ALL registered jobs?
            <Box component="span" fontWeight="bold" display="block" mt={1}>
              This will cancel all jobs in the queue.
            </Box>
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={cancelClearAllJobs}
            color="primary"
            disabled={clearingAll}
          >
            Cancel
          </Button>
          <Button
            onClick={confirmClearAllJobs}
            color="error"
            disabled={clearingAll}
            startIcon={clearingAll ? <CircularProgress size={20} /> : null}
          >
            {clearingAll ? "Clearing..." : "Clear All"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default JobQueueWidget;
