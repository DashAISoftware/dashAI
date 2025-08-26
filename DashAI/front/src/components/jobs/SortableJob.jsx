import React from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Typography,
  Tooltip,
  Chip,
  Box,
} from "@mui/material";
import ErrorIcon from "@mui/icons-material/Error";
import { StatusIcon, statusText } from "./JobQueueWidget";

export function SortableJob({ job, onClick, getRelativeTime }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: job.id,
    disabled: job.status !== "not_started",
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    backgroundColor: isDragging
      ? "rgba(0, 0, 0, 0.05)"
      : job.status === "started"
      ? "rgba(25, 118, 210, 0.08)"
      : undefined,
    cursor: job.status === "not_started" ? "grab" : "pointer",
    zIndex: isDragging ? 1 : "auto",
    // Estilo para trabajos de alta prioridad
    borderLeft:
      job.status === "not_started" && job.priority > 50
        ? "3px solid #1976d2"
        : undefined,
  };

  return (
    <ListItem
      ref={setNodeRef}
      button
      divider
      onClick={() => onClick(job)}
      sx={style}
      {...attributes}
      {...listeners}
    >
      <ListItemIcon sx={{ minWidth: 40 }}>
        <StatusIcon status={job.status} />
      </ListItemIcon>
      <ListItemText
        primary={
          <Box display="flex" alignItems="center">
            <Tooltip title={job.task_type || ""}>
              <Typography variant="body2" noWrap>
                {job.task_type ? job.task_type.split(".").pop() : "Unknown Job"}
              </Typography>
            </Tooltip>

            {/* Badge de prioridad para jobs pendientes */}
            {job.status === "not_started" && (
              <Tooltip title="Priority">
                <Chip
                  size="small"
                  label={`P${job.priority || 0}`}
                  color={job.priority > 50 ? "primary" : "default"}
                  sx={{ ml: 1, height: 16, fontSize: "0.6rem" }}
                />
              </Tooltip>
            )}
          </Box>
        }
        secondary={
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "flex", alignItems: "center" }}
          >
            <span>{statusText[job.status] || job.status}</span>
            {job.status === "error" && (
              <Tooltip title={job.error_msg || "Unknown error"}>
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
  );
}
