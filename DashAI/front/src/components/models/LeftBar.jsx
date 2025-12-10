import { useState, useEffect, useRef } from "react";
import {
  Box,
  Divider,
  Typography,
  IconButton,
  Collapse,
  ListItemButton,
  ListItemText,
  TextField,
} from "@mui/material";
import {
  ChevronLeft,
  KeyboardArrowDown,
  KeyboardArrowRight,
} from "@mui/icons-material";
import StorageIcon from "@mui/icons-material/Storage";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import Footer from "../threeSectionLayout/Footer";
import BarHeader from "../threeSectionLayout/BarHeader";
import SideBar from "../threeSectionLayout/SideBar";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import ItemMenu from "../threeSectionLayout/ItemMenu";

export default function ModelsLeftBar({
  datasets = [],
  selectedDatasetId,
  sessions = [],
  selectedSessionId,
  tasks = [],
  onDatasetClick,
  onSessionClick,
  onSessionDelete,
  onSessionEdit,
  onToggle,
  handleNewSessionButton,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredDatasets, setFilteredDatasets] = useState(datasets);
  const [filteredSessions, setFilteredSessions] = useState(sessions);
  const [openSections, setOpenSections] = useState({});
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editedName, setEditedName] = useState("");

  // Helper function to get display name from task
  const getTaskDisplayName = (taskName) => {
    if (!taskName) return "Other";
    const task = tasks.find((t) => t.name === taskName);
    return (
      task?.metadata?.display_name ||
      taskName
        .replace("Task", "")
        .replace(/([A-Z])/g, " $1")
        .trim()
    );
  };

  useEffect(() => {
    // Initialize all task sections as closed
    const displayNames = [
      ...new Set(
        sessions.map((session) => getTaskDisplayName(session.task_name)),
      ),
    ];
    const initialOpenState = {};
    displayNames.forEach((displayName) => {
      initialOpenState[displayName] = false;
    });
    setOpenSections(initialOpenState);
  }, [sessions, tasks]);

  useEffect(() => {
    const q = searchQuery.trim().toLowerCase();

    if (!q) {
      setFilteredDatasets(datasets);
      setFilteredSessions(sessions);
      return;
    }

    const match = (item) => (item?.name ?? "").toLowerCase().includes(q);

    setFilteredDatasets(datasets.filter(match));
    setFilteredSessions(sessions.filter(match));
  }, [searchQuery, datasets, sessions]);

  const handleSearchChange = (e) => setSearchQuery(e.target.value);

  const toggleSection = (taskName) => {
    setOpenSections((prev) => ({
      ...prev,
      [taskName]: !prev[taskName],
    }));
  };

  const handleEditSession = (sessionId, sessionName) => {
    setEditingSessionId(sessionId);
    setEditedName(sessionName);
  };

  const handleSaveEdit = async (sessionId) => {
    if (
      editedName.trim() &&
      editedName.trim() !== sessions.find((s) => s.id === sessionId)?.name
    ) {
      try {
        if (onSessionEdit) {
          await onSessionEdit(sessionId, editedName.trim());
        }
      } catch (error) {
        console.error("Error editing session:", error);
      }
    }
    setEditingSessionId(null);
    setEditedName("");
  };

  const handleCancelEdit = () => {
    setEditingSessionId(null);
    setEditedName("");
  };

  const handleKeyDown = (e, sessionId) => {
    if (e.key === "Enter") {
      handleSaveEdit(sessionId);
    } else if (e.key === "Escape") {
      handleCancelEdit();
    }
  };

  const getDatasetDescription = (dataset) => {
    return (
      dataset.description ||
      `${dataset.total_rows || 0} rows, ${dataset.total_columns || 0} cols`
    );
  };

  const getSessionDescription = (session) => {
    if (session.dataloader_name && datasets.length > 0) {
      const associatedDataset = datasets.find(
        (dataset) => dataset.name === session.dataloader_name,
      );
      return associatedDataset?.name
        ? `from ${associatedDataset.name} dataset`
        : "No dataset";
    }
    return session.description || "";
  };

  // Group sessions by display_name
  const groupedSessions = filteredSessions?.reduce((groups, session) => {
    const displayName = getTaskDisplayName(session.task_name);
    if (!groups[displayName]) {
      groups[displayName] = [];
    }
    groups[displayName].push(session);
    return groups;
  }, {});

  return (
    <SideBar>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pr: 2,
        }}
      >
        <BarHeader />
        <IconButton
          size="small"
          onClick={onToggle}
          sx={{ color: "text.secondary" }}
        >
          <ChevronLeft />
        </IconButton>
      </Box>
      <Divider sx={{ width: "100%", bgcolor: "#252836" }} />

      {/* Create new item button */}
      <Box p={2} sx={{ height: "64px", display: "flex", alignItems: "center" }}>
        {selectedDatasetId || selectedSessionId ? (
          <NewItemButton
            onClick={handleNewSessionButton}
            title="New Dataset/Session"
          />
        ) : (
          <Typography variant="body1" color="textSecondary">
            Models Module
          </Typography>
        )}
      </Box>

      {/* Search bar global */}
      <Box px={2} pb={2} flex={"0 0 auto"}>
        <SearchBar
          placeholder="Search Datasets and Sessions"
          value={searchQuery}
          onChange={handleSearchChange}
        />
      </Box>

      <Divider sx={{ width: "90%", bgcolor: "#252836", mx: "auto" }} />

      {/* Scrollable content */}
      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        <CollapsibleList
          items={filteredDatasets}
          selectedItemId={selectedDatasetId}
          onItemClick={onDatasetClick}
          defaultOpen={true}
          title="Available Datasets"
          Icon={StorageIcon}
          getItemDescription={getDatasetDescription}
        />

        <Divider sx={{ width: "90%", bgcolor: "#252836", mx: "auto" }} />

        {/* Sessions grouped by task */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            overflow: "auto",
            px: 2,
            pt: 2,
          }}
        >
          {/* Header */}
          <Box display="flex" alignItems="center" py={0.5} px={1} mb={0.5}>
            <ModelTrainingIcon sx={{ color: "#16FFFF", mr: 1, fontSize: 20 }} />
            <Typography>Sessions</Typography>
            <Box
              sx={{
                ml: 1,
                bgcolor: "#374151",
                color: "white",
                borderRadius: "50%",
                width: 20,
                height: 20,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 12,
              }}
            >
              {filteredSessions?.length}
            </Box>
          </Box>

          {/* Sessions grouped by task */}
          {Object.entries(groupedSessions || {}).map(
            ([taskName, taskSessions]) => (
              <Box key={taskName} mb={1}>
                {/* Task Header */}
                <Box
                  display="flex"
                  alignItems="center"
                  sx={{
                    cursor: "pointer",
                    py: 0.5,
                    px: 1,
                    borderRadius: 1,
                    "&:hover": {
                      bgcolor: "rgba(255, 255, 255, 0.05)",
                    },
                  }}
                  onClick={() => toggleSection(taskName)}
                >
                  {openSections[taskName] ? (
                    <KeyboardArrowDown
                      sx={{ fontSize: 20, color: "#16FFFF" }}
                    />
                  ) : (
                    <KeyboardArrowRight
                      sx={{ fontSize: 20, color: "#16FFFF" }}
                    />
                  )}
                  <Typography
                    sx={{
                      ml: 1,
                      fontSize: "0.9rem",
                      fontWeight: "medium",
                      textTransform: "capitalize",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      wordBreak: "break-all",
                      whiteSpace: "nowrap",
                      width: "100%",
                    }}
                  >
                    {taskName}
                  </Typography>
                  <Box
                    sx={{
                      ml: 1,
                      bgcolor: "#374151",
                      color: "white",
                      borderRadius: "50%",
                      width: 20,
                      height: 20,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 12,
                    }}
                  >
                    {taskSessions.length}
                  </Box>
                </Box>

                {/* Sessions List */}
                <Collapse in={openSections[taskName]} timeout="auto">
                  <Box pl={2}>
                    {taskSessions.map((session) => {
                      const isEditing = editingSessionId === session.id;

                      const handleEditClick = () => {
                        handleEditSession(session.id, session.name);
                      };

                      return (
                        <ListItemButton
                          key={session.id}
                          selected={session.id === selectedSessionId}
                          onClick={
                            isEditing
                              ? undefined
                              : () => onSessionClick(session.id)
                          }
                          sx={{
                            py: 0.75,
                            borderRadius: 1,
                            mb: 0.5,
                            cursor: isEditing ? "default" : "pointer",
                            "&.Mui-selected": {
                              bgcolor: "rgba(22, 255, 255, 0.15)",
                              "&:hover": {
                                bgcolor: "rgba(22, 255, 255, 0.2)",
                              },
                            },
                            "&:hover": {
                              bgcolor: "rgba(255, 255, 255, 0.05)",
                            },
                          }}
                        >
                          {isEditing ? (
                            <TextField
                              autoFocus
                              value={editedName}
                              onChange={(e) => setEditedName(e.target.value)}
                              onKeyDown={(e) => handleKeyDown(e, session.id)}
                              onBlur={() => handleSaveEdit(session.id)}
                              size="small"
                              variant="outlined"
                              sx={{
                                flex: 1,
                                "& .MuiInputBase-input": {
                                  fontSize: 14,
                                  padding: "4px 8px",
                                },
                              }}
                            />
                          ) : (
                            <ListItemText
                              primary={session.name}
                              secondary={getSessionDescription(session)}
                              primaryTypographyProps={{
                                variant: "body2",
                                noWrap: true,
                              }}
                              secondaryTypographyProps={{
                                variant: "caption",
                                noWrap: true,
                              }}
                            />
                          )}
                          {!isEditing && (
                            <ItemMenu
                              itemId={session.id}
                              onDelete={
                                onSessionDelete
                                  ? () => onSessionDelete(session.id)
                                  : undefined
                              }
                              onEdit={
                                onSessionEdit ? handleEditClick : undefined
                              }
                            />
                          )}
                        </ListItemButton>
                      );
                    })}
                  </Box>
                </Collapse>
              </Box>
            ),
          )}
        </Box>
      </Box>

      {/* Footer */}
      <Footer />
    </SideBar>
  );
}
