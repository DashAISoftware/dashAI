import React, { useState, useEffect } from "react";
import { Box, Divider, Typography, IconButton } from "@mui/material";
import { ChevronLeft } from "@mui/icons-material";
import StorageIcon from "@mui/icons-material/Storage";
import Biotech from "@mui/icons-material/Biotech";
import Footer from "../threeSectionLayout/Footer";
import BarHeader from "../threeSectionLayout/BarHeader";
import SideBar from "../threeSectionLayout/SideBar";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import GroupedCollapsibleList from "../threeSectionLayout/GroupedCollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import InfoSessionModal from "./InfoSessionModal";

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
  const [openSections, setOpenSections] = useState({});
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);

  const getTaskDisplayName = React.useCallback(
    (taskName) => {
      if (!taskName) return "Other";
      const task = tasks.find((t) => t.name === taskName);
      return (
        task?.metadata?.display_name ||
        taskName
          .replace("Task", "")
          .replace(/([A-Z])/g, " $1")
          .trim()
      );
    },
    [tasks],
  );

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
    setOpenSections((prev) => {
      // Only update if display names have changed
      const prevKeys = Object.keys(prev).sort().join(",");
      const newKeys = Object.keys(initialOpenState).sort().join(",");
      if (prevKeys === newKeys) return prev;
      return initialOpenState;
    });
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

  const handleSessionInfo = React.useCallback(
    (sessionId) => {
      const session = sessions.find((s) => s.id === sessionId);
      if (session) {
        setSelectedInfoSession(session);
      }
    },
    [sessions],
  );

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

        <GroupedCollapsibleList
          groups={groupedSessions}
          selectedItemId={selectedSessionId}
          onItemClick={onSessionClick}
          onItemDelete={onSessionDelete}
          onItemEdit={onSessionEdit}
          onItemInfo={handleSessionInfo}
          title="Sessions"
          Icon={Biotech}
          getItemDescription={getSessionDescription}
          initialOpenGroups={openSections}
        />
      </Box>

      {/* Footer */}
      <Footer />

      {/* Session Info Modal */}
      {selectedInfoSession && (
        <InfoSessionModal
          sessionData={selectedInfoSession}
          datasets={datasets}
          tasks={tasks}
          open={!!selectedInfoSession}
          onClose={() => setSelectedInfoSession(null)}
        />
      )}
    </SideBar>
  );
}
