import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Badge,
  Collapse,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Tooltip,
  Fade,
  Divider,
  Chip,
} from "@mui/material";
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
import useJobQueue from "../../hooks/useJobQueue";
import useJobPolling, { forceRefreshNow } from "../../hooks/useJobPolling";

// Exportar estos componentes para uso general
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
  // Estado local
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

  // Usar el hook existente que ya funcionaba
  const { jobs, loading, error, refetch } = useJobQueue(500);

  // Usar el polling existente que ya funcionaba
  useJobPolling(
    3000,
    useCallback(
      (changes, meta) => {
        const hasChanges = Array.isArray(changes) && changes.length > 0;
        const justCompleted = !!meta?.recentlyCompleted;
        const queueNotEmpty = meta?.queueEmpty === false;

        if (hasChanges || justCompleted) {
          setTimeout(() => refetch(), justCompleted ? 500 : 0);
          return;
        }

        if (queueNotEmpty) {
          refetch();
        }
      },
      [refetch],
    ),
  );

  // Calcular jobs filtrados
  const activeJobs = jobs.filter(
    (job) => job.status === "started" || job.status === "not_started",
  );
  const finishedJobs = jobs.filter((job) => job.status === "finished");
  const errorJobs = jobs.filter((job) => job.status === "error");

  // Guardar el estado de expansión en localStorage
  useEffect(() => {
    try {
      localStorage.setItem("jobQueueWidgetExpanded", expanded.toString());
    } catch (e) {}
  }, [expanded]);

  // Expandir automáticamente cuando hay jobs activos
  useEffect(() => {
    if (activeJobs.length > 0 && !expanded) {
      setExpanded(true);
    }
  }, [activeJobs.length, expanded, jobs]);

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
    console.log("Manual refresh triggered");
    forceRefreshNow(); // Usar la función existente para forzar un refresh
  };

  const getJobsToShow = () => {
    if (showFinished) {
      return jobs.slice(0, 10);
    } else {
      return [...activeJobs, ...errorJobs]
        .sort((a, b) => new Date(b.last_update) - new Date(a.last_update))
        .slice(0, 10);
    }
  };

  const getRelativeTime = (timestamp) => {
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
      if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)}h ago`;
      return `${Math.floor(diffSeconds / 86400)}d ago`;
    } catch (e) {
      console.error("Error parsing time:", e, timestamp);
      return "time unknown";
    }
  };

  const jobsToShow = getJobsToShow();

  return (
    <>
      <Fade in={true}>
        <Paper
          elevation={6}
          sx={{
            position: "fixed",
            bottom: (theme) => theme.spacing(3),
            right: (theme) => theme.spacing(3),
            zIndex: 1000,
            width: 320,
            maxHeight: "80vh",
            display: "flex",
            flexDirection: "column",
            boxShadow: (theme) => theme.shadows[6],
            borderRadius: (theme) => theme.shape.borderRadius,
            overflow: "hidden",
            transition: "all 0.3s ease",
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
                  maxHeight: 280,
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
                        button
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
                              <Tooltip title={job.task_type || ""}>
                                <Typography variant="body2" noWrap>
                                  {job.task_type
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
                          <Typography variant="caption" color="text.secondary">
                            {getRelativeTime(job.last_update)}
                          </Typography>
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
    </>
  );
};

export default JobQueueWidget;
