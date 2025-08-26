import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Badge,
  Collapse,
  List,
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
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import {
  restrictToVerticalAxis,
  restrictToParentElement,
} from "@dnd-kit/modifiers";
import { SortableJob } from "./SortableJob";
import { updateJobPriority } from "../../api/job";

// Exportar estos componentes para usarlos en SortableJob
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
  const [items, setItems] = useState([]);

  // Configurar sensores para dnd-kit
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5, // 5px de movimiento antes de activar el drag
      },
    }),
  );

  // Usar el hook existente que ya funcionaba
  const { jobs, loading, error, refetch } = useJobQueue(500);

  // Actualizar los items cuando cambien los jobs
  useEffect(() => {
    const jobsToShow = getJobsToShow();
    setItems(jobsToShow);
  }, [jobs, showFinished]);

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
    let result;

    if (showFinished) {
      result = jobs.slice(0, 10);
    } else {
      result = [...activeJobs, ...errorJobs].slice(0, 10);
    }

    // Ordenar primero por prioridad para jobs pendientes, luego por fecha para el resto
    return result.sort((a, b) => {
      // Si ambos son "not_started", ordenar por prioridad (mayor primero)
      if (a.status === "not_started" && b.status === "not_started") {
        // Si no tienen prioridad, usar 0 como valor predeterminado
        const priorityA = a.priority || 0;
        const priorityB = b.priority || 0;
        return priorityB - priorityA; // Mayor prioridad primero
      }

      // Si solo uno es "not_started", va primero
      if (a.status === "not_started" && b.status !== "not_started") return -1;
      if (a.status !== "not_started" && b.status === "not_started") return 1;

      // Para el resto, ordenar por fecha (más reciente primero)
      return new Date(b.last_update) - new Date(a.last_update);
    });
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;

    if (!over || active.id === over.id) return;

    // Obtener los índices directamente del arreglo actual
    const oldIndex = items.findIndex((job) => job.id === active.id);
    const newIndex = items.findIndex((job) => job.id === over.id);

    if (oldIndex === -1 || newIndex === -1) return;

    // Crear nueva lista ordenada
    const newItems = arrayMove([...items], oldIndex, newIndex);

    // Actualizar estado local para UI inmediata
    setItems(newItems);

    try {
      // Extraer solo los jobs pendientes (not_started)
      const pendingJobs = newItems.filter(
        (job) => job.status === "not_started",
      );

      // Preparar array de actualizaciones para ejecutar en secuencia
      const updatePromises = [];

      // Recalcular prioridades para TODOS los jobs pendientes
      pendingJobs.forEach((job, index) => {
        // Usar un sistema de prioridades con espacio entre valores
        // Base 10000, decrementos de 100 para dejar espacio para inserciones futuras
        const newPriority = 10000 - index * 100;

        // Solo actualizar si la prioridad ha cambiado
        if (job.priority !== newPriority) {
          console.log(`Updating job ${job.id} to priority ${newPriority}`);

          // Actualizar localmente
          job.priority = newPriority;

          // Añadir a la lista de actualizaciones para el backend
          updatePromises.push(updateJobPriority(job.id, newPriority));
        }
      });

      // Ejecutar todas las actualizaciones en paralelo
      if (updatePromises.length > 0) {
        await Promise.all(updatePromises);

        // No refrescar automáticamente - confiamos en nuestros datos locales
        // Solo refrescar después de un tiempo para sincronizar con backend
        setTimeout(() => {
          // Usar una bandera para evitar deshacer nuestros cambios
          const preservePriorities = true;
          forceRefreshNow(preservePriorities);
        }, 2000);
      }
    } catch (error) {
      console.error("Error updating job priorities:", error);
      // En caso de error, refrescar para volver al estado real del backend
      setTimeout(() => forceRefreshNow(), 500);
    }
  };

  // Añadir el manejo para nuevos jobs con prioridad cero
  useEffect(() => {
    // Este efecto maneja jobs nuevos con prioridad 0
    const jobsToProcess = getJobsToShow();

    // Identificar jobs pendientes sin prioridad que necesiten ser posicionados
    const pendingJobs = jobsToProcess.filter(
      (job) => job.status === "not_started",
    );
    const newJobsWithoutPriority = pendingJobs.filter((job) => !job.priority);

    if (newJobsWithoutPriority.length > 0) {
      // Encontrar la prioridad más baja actual
      let lowestPriority = 0;
      pendingJobs.forEach((job) => {
        if (job.priority && job.priority > lowestPriority) {
          lowestPriority = job.priority;
        }
      });

      // Nuevos jobs deberían ir después de los existentes
      const startPriority = lowestPriority > 0 ? lowestPriority - 100 : 10000;

      // Preparar actualizaciones
      const updatePromises = [];

      // Asignar prioridades a los nuevos jobs
      newJobsWithoutPriority.forEach((job, index) => {
        const newPriority = startPriority - index * 100;
        job.priority = newPriority;
        updatePromises.push(updateJobPriority(job.id, newPriority));
      });

      // Aplicar actualizaciones en silencio
      if (updatePromises.length > 0) {
        Promise.all(updatePromises).catch((err) =>
          console.error("Error setting initial priorities:", err),
        );
      }

      // Actualizar items para reflejar las nuevas prioridades
      setItems([...jobsToProcess]);
    }
  }, [jobs]);

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

                {items.length > 0 && (
                  <DndContext
                    sensors={sensors}
                    collisionDetection={closestCenter}
                    onDragEnd={handleDragEnd}
                    modifiers={[
                      restrictToVerticalAxis,
                      restrictToParentElement,
                    ]}
                  >
                    <SortableContext
                      items={items.map((job) => job.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <List dense disablePadding>
                        {items.map((job) => (
                          <SortableJob
                            key={job.id}
                            job={job}
                            onClick={handleJobClick}
                            getRelativeTime={getRelativeTime}
                          />
                        ))}
                      </List>
                    </SortableContext>
                  </DndContext>
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
