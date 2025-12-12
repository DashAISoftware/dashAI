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

        <CollapsibleList
          items={filteredSessions}
          selectedItemId={selectedSessionId}
          onItemClick={onSessionClick}
          onItemDelete={onSessionDelete}
          onItemEdit={onSessionEdit}
          defaultOpen={true}
          title="Sessions"
          Icon={ModelTrainingIcon}
          getItemDescription={getSessionDescription}
        />
      </Box>

      {/* Footer */}
      <Footer />
    </SideBar>
  );
}
