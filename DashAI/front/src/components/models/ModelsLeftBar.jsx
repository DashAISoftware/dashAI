import React, { useState, useEffect } from "react";
import { Box, Divider, Typography, IconButton } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { ChevronLeft } from "@mui/icons-material";
import StorageIcon from "@mui/icons-material/Storage";
import Biotech from "@mui/icons-material/Biotech";
import Footer from "../threeSectionLayout/Footer";
import BarHeader from "../threeSectionLayout/BarHeader";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import GroupedCollapsibleList from "../threeSectionLayout/GroupedCollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import InfoSessionModal from "./InfoSessionModal";
import { useTranslation } from "react-i18next";
import { useModels } from "./ModelsContext";

export default function ModelsLeftBar({
  onDatasetDelete,
  onDatasetEdit,
  onSessionClick,
  onSessionEdit,
  onToggle,
  handleNewSessionButton,
}) {
  const {
    deleteSessionById,
    setSelectedSessionId,
    setSelectedSession,
    setSelectedTask,
    setStep,
    selectDataset,
    datasets,
    selectedDatasetId,
    sessions,
    tasks,
    selectedSessionId,
  } = useModels();

  const theme = useTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredDatasets, setFilteredDatasets] = useState(datasets);
  const [filteredSessions, setFilteredSessions] = useState(sessions);
  const [openSections, setOpenSections] = useState({});
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);
  const { t } = useTranslation(["models", "datasets", "common"]);

  const getTaskDisplayName = React.useCallback(
    (taskName) => {
      if (!taskName) return t("common:other");
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
    return t("datasets:label.datasetDescription", {
      rows: dataset.total_rows || 0,
      columns: dataset.total_columns || 0,
    });
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

  const onDatasetClick = (datasetId) => {
    selectDataset(datasetId);
    setSelectedSessionId(null);
    setSelectedTask(null);
    setStep(2); // Use a different step to show DatasetVisualization
  };

  const onSessionDelete = async (id) => {
    const success = await deleteSessionById(id);
    if (!success) return;
    if (id === selectedSessionId) {
      setSelectedSessionId(null);
      setSelectedSession(null);
      setStep(0);
      setSelectedTask(null);
    }
  };

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
      <Divider sx={{ width: "100%", bgcolor: theme.palette.ui.borderDark }} />

      {/* Create new item button */}
      <Box p={2} sx={{ height: "64px", display: "flex", alignItems: "center" }}>
        {selectedDatasetId || selectedSessionId ? (
          <NewItemButton
            onClick={handleNewSessionButton}
            title={t("models:button.newSession")}
          />
        ) : (
          <Typography variant="body1" color="textSecondary">
            {t("models:label.modelsModule")}
          </Typography>
        )}
      </Box>

      {/* Search bar global */}
      <Box px={2} pb={2} flex={"0 0 auto"}>
        <SearchBar
          placeholder={t("models:label.searchDatasetsSessions")}
          value={searchQuery}
          onChange={handleSearchChange}
        />
      </Box>

      <Divider
        sx={{ width: "90%", bgcolor: theme.palette.ui.borderDark, mx: "auto" }}
      />

      {/* Scrollable content */}
      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        <CollapsibleList
          items={filteredDatasets}
          selectedItemId={selectedDatasetId}
          onItemClick={onDatasetClick}
          onItemDelete={onDatasetDelete}
          onItemEdit={onDatasetEdit}
          defaultOpen={true}
          title={t("datasets:label.availableDatasets")}
          Icon={StorageIcon}
          getItemDescription={getDatasetDescription}
        />

        <Divider
          sx={{
            width: "90%",
            bgcolor: theme.palette.ui.borderDark,
            mx: "auto",
          }}
        />

        <GroupedCollapsibleList
          groups={groupedSessions}
          selectedItemId={selectedSessionId}
          onItemClick={onSessionClick}
          onItemDelete={onSessionDelete}
          onItemEdit={onSessionEdit}
          onItemInfo={handleSessionInfo}
          title={t("common:sessions")}
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
