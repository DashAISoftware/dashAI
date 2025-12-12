import { useState, useEffect } from "react";
import { Box, Divider, Typography, IconButton } from "@mui/material";
import { ChevronLeft } from "@mui/icons-material";
import StorageIcon from "@mui/icons-material/Storage";
import ModelTrainingIcon from "@mui/icons-material/ModelTraining";
import Footer from "../threeSectionLayout/Footer";
import BarHeader from "../threeSectionLayout/BarHeader";
import SideBar from "../threeSectionLayout/SideBar";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";

export default function ModelsLeftBar({
  datasets = [],
  selectedDatasetId,
  sessions = [],
  selectedSessionId,
  tasks = [],
  onDatasetClick,
  onDatasetDelete,
  onDatasetEdit,
  onSessionClick,
  onSessionDelete,
  onSessionEdit,
  onToggle,
  handleNewSessionButton,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredDatasets, setFilteredDatasets] = useState(datasets);
  const [filteredSessions, setFilteredSessions] = useState(sessions);

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

  // Group sessions by task
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
          onItemDelete={onDatasetDelete}
          onItemEdit={onDatasetEdit}
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
            display: "flex",
            flexDirection: "column",
          }}
        >
          {Object.entries(groupedSessions || {}).map(
            ([taskName, taskSessions]) => (
              <Box key={taskName}>
                <CollapsibleList
                  items={taskSessions}
                  selectedItemId={selectedSessionId}
                  onItemClick={onSessionClick}
                  onItemDelete={onSessionDelete}
                  onItemEdit={onSessionEdit}
                  defaultOpen={false}
                  title={`${taskName} Sessions`}
                  Icon={ModelTrainingIcon}
                  getItemDescription={getSessionDescription}
                />
                {Object.keys(groupedSessions).indexOf(taskName) <
                  Object.keys(groupedSessions).length - 1 && (
                  <Divider
                    sx={{ width: "90%", bgcolor: "#252836", mx: "auto", my: 1 }}
                  />
                )}
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
