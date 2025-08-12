import { useState, useEffect } from "react";
import { Box, Divider, Typography } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import DescriptionIcon from "@mui/icons-material/Description";
import Footer from "../threeSectionLayout/Footer";
import BarHeader from "../threeSectionLayout/BarHeader";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/SideBar";

export default function DatasetsNotebooksBar({
  datasets = [],
  selectedDatasetId,
  notebooks = [],
  selectedNotebookId,
  onDatasetClick,
  onDatasetDelete,
  onNotebookClick,
  onNotebookDelete,
  handleNewSessionButton,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filteredDatasets, setFilteredDatasets] = useState(datasets);
  const [filteredNotebooks, setFilteredNotebooks] = useState(notebooks);

  useEffect(() => {
    const q = searchQuery.trim().toLowerCase();

    if (!q) {
      setFilteredDatasets(datasets);
      setFilteredNotebooks(notebooks);
      return;
    }

    const match = (item) => (item?.name ?? "").toLowerCase().includes(q);

    setFilteredDatasets(datasets.filter(match));
    setFilteredNotebooks(notebooks.filter(match));
  }, [searchQuery, datasets, notebooks]);

  const handleSearchChange = (e) => setSearchQuery(e.target.value);

  return (
    <SideBar>
      {/* Header */}
      <BarHeader />
      <Divider sx={{ width: "100%", bgcolor: "#252836" }} />

      {/* Create new item button */}
      {selectedDatasetId || selectedNotebookId ? (
        <NewItemButton
          onClick={handleNewSessionButton}
          title="New Dataset/Notebook"
        />
      ) : (
        <Box px={2} py={1}>
          <Typography variant="body1" color="textSecondary">
            Dataset Module
          </Typography>
        </Box>
      )}

      {/* Search bar global */}
      <Box px={2} py={1} flex="0 0 auto">
        <SearchBar
          placeholder="Search datasets and notebooks"
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
          defaultOpen={true}
          title="Available Datasets"
          Icon={StorageIcon}
        />

        <Divider sx={{ width: "90%", bgcolor: "#252836", mx: "auto" }} />

        <CollapsibleList
          items={filteredNotebooks}
          selectedItemId={selectedNotebookId}
          onItemClick={onNotebookClick}
          onItemDelete={onNotebookDelete}
          defaultOpen={true}
          title="Notebooks"
          Icon={DescriptionIcon}
        />
      </Box>

      {/* Footer */}
      <Footer />
    </SideBar>
  );
}
