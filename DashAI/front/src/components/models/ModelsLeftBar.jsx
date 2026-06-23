import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Divider, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import Biotech from "@mui/icons-material/Biotech";
import ViewModuleIcon from "@mui/icons-material/ViewModule";
import Footer from "../threeSectionLayout/Footer";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import DatasetFolderList from "../threeSectionLayout/DatasetFolderList";
import GroupedCollapsibleList from "../threeSectionLayout/GroupedCollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import InfoSessionModal from "./InfoSessionModal";
import { useTranslation } from "react-i18next";
import { useModels } from "./ModelsContext";

export default function ModelsLeftBar({ onToggle }) {
  const {
    deleteSessionById,
    setSelectedSessionId,
    setSelectedSession,
    setSelectedTask,
    setStep,
    selectDataset,
    datasets,
    selectedDatasetId,
    replaceDatasets,
    sessions,
    tasks,
    selectedSessionId,
    setSessions,
    deleteDataset,
    editDataset,
    editSession,
    folders,
    createFolder,
    renameFolder,
    deleteFolderById,
    moveDatasetToFolder,
  } = useModels();
  const navigate = useNavigate();

  const theme = useTheme();
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredDatasets, setFilteredDatasets] = useState(datasets);
  const [filteredSessions, setFilteredSessions] = useState(sessions);
  const [openSections, setOpenSections] = useState({});
  const [selectedInfoSession, setSelectedInfoSession] = useState(null);
  const { t } = useTranslation(["models", "datasets", "common"]);

  const SEARCH_THRESHOLD = 10;
  const totalItems = datasets.length + sessions.length;

  useEffect(() => {
    if (totalItems <= SEARCH_THRESHOLD) setSearchQuery("");
  }, [totalItems]);

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

  const getDatasetDeleteConfirmationContent = (dataset) =>
    t(
      "datasets:label.confirmDeleteDataset",
      'Are you sure you want to delete the dataset "{{name}}"? This action cannot be undone.',
      { name: dataset.name },
    );

  const getDatasetDeleteConfirmationWarning = () =>
    t(
      "datasets:label.confirmDeleteDatasetLinkedWarning",
      "All notebooks and sessions linked to this dataset will also be deleted.",
    );

  const getSessionDeleteConfirmationContent = (session) =>
    t(
      "models:label.confirmDeleteSession",
      'Are you sure you want to delete the session "{{name}}"? This action cannot be undone.',
      { name: session.name },
    );

  const getDatasetDescription = (dataset) => {
    const base = t("datasets:label.datasetDescription", {
      rows: dataset.total_rows || 0,
      columns: dataset.total_columns || 0,
    });
    return dataset.task ? `${dataset.task} | ${base}` : base;
  };

  const getSessionDescription = (session) => {
    if (session.dataset_id && datasets.length > 0) {
      const associatedDataset = datasets.find(
        (dataset) => dataset.id === session.dataset_id,
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

  // Sort grouped sessions to maintain consistent order
  const sortedGroupedSessions = groupedSessions
    ? Object.keys(groupedSessions)
        .sort()
        .reduce((sorted, key) => {
          sorted[key] = groupedSessions[key];
          return sorted;
        }, {})
    : {};

  const onDatasetClick = (datasetId) => {
    navigate(`/app/models/datasets/${datasetId}`);
  };

  const onSessionDelete = async (id) => {
    const success = await deleteSessionById(id);
    if (!success) return;
    if (id === selectedSessionId) {
      navigate("/app/models");
    }
  };

  const onDatasetDelete = (id) => {
    if (id === selectedDatasetId) {
      navigate("/app/models");
    }

    replaceDatasets((prevDatasets) =>
      prevDatasets.filter((dataset) => dataset.id !== id),
    );

    setSessions((prevSessions) => {
      const filteredSessions = prevSessions.filter(
        (session) => session.dataset_id !== id,
      );

      if (
        selectedSessionId &&
        prevSessions.find(
          (session) =>
            session.id === selectedSessionId && session.dataset_id === id,
        )
      ) {
        navigate("/app/models");
      }

      return filteredSessions;
    });

    deleteDataset(id);
  };

  const onSessionClick = (sessionId) => {
    navigate(`/app/models/sessions/${sessionId}`);
  };

  const handleNewSessionButton = () => {
    navigate("/app/models");
  };

  return (
    <SideBar>
      {/* Create new item button */}
      <Box p={4} sx={{ height: "64px", display: "flex", alignItems: "center" }}>
        {selectedDatasetId || selectedSessionId ? (
          <NewItemButton
            onClick={handleNewSessionButton}
            title={t("models:button.modelsHub")}
            EndIcon={ViewModuleIcon}
          />
        ) : (
          <Typography variant="body1" color="textSecondary">
            {t("models:label.modelsModule")}
          </Typography>
        )}
      </Box>

      {/* Search bar global */}
      {totalItems > SEARCH_THRESHOLD && (
        <Box px={4} pb={4} flex={"0 0 auto"}>
          <SearchBar
            placeholder={t("models:label.searchDatasetsSessions")}
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </Box>
      )}

      <Divider
        sx={{ width: "90%", bgcolor: theme.palette.ui.borderDark, mx: "auto" }}
      />

      {/* Scrollable content */}
      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        <DatasetFolderList
          datasets={filteredDatasets}
          folders={folders}
          selectedItemId={selectedDatasetId}
          onItemClick={onDatasetClick}
          onItemDelete={onDatasetDelete}
          onItemEdit={editDataset}
          title={t("datasets:label.availableDatasets")}
          getItemDescription={getDatasetDescription}
          getDeleteConfirmationContent={getDatasetDeleteConfirmationContent}
          getDeleteConfirmationWarning={getDatasetDeleteConfirmationWarning}
          onCreateFolder={createFolder}
          onRenameFolder={renameFolder}
          onDeleteFolder={deleteFolderById}
          onMoveDataset={moveDatasetToFolder}
        />

        <Divider
          sx={{
            width: "90%",
            bgcolor: theme.palette.ui.borderDark,
            mx: "auto",
          }}
        />

        <GroupedCollapsibleList
          groups={sortedGroupedSessions}
          selectedItemId={selectedSessionId}
          onItemClick={onSessionClick}
          onItemDelete={onSessionDelete}
          onItemEdit={editSession}
          onItemInfo={handleSessionInfo}
          title={t("common:sessions")}
          Icon={Biotech}
          getItemDescription={getSessionDescription}
          getDeleteConfirmationContent={getSessionDeleteConfirmationContent}
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
