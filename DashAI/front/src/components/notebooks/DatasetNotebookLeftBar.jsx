import { useState, useEffect } from "react";
import { Box, Divider, Typography, IconButton } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import DescriptionIcon from "@mui/icons-material/Description";
import Footer from "../threeSectionLayout/Footer";
import BarHeader from "../threeSectionLayout/BarHeader";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import InfoNotebookModal from "./notebook/InfoNotebookModal";
import { ChevronLeft } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

import { useDatasetsAndNotebooks } from "../custom/contexts/DatasetsAndNotebooksContext";

export default function DatasetsNotebooksLeftBar({
  onToggle,
  handleNewSessionButton,
}) {
  const {
    datasets,
    notebooks,
    selectedDatasetId,
    selectedNotebookId,
    selectDataset,
    selectNotebook,
    clearSelectedNotebook,
    setStep,
    setSelectedOption,
    clearSelectedDataset,
    deleteDatasetLocal,
    deleteDatasetRemote,
    removeNotebooksByDatasetId,
    editDataset,
    editNotebook,
    deleteNotebookById,
  } = useDatasetsAndNotebooks();

  const [filteredDatasets, setFilteredDatasets] = useState(datasets);
  const [filteredNotebooks, setFilteredNotebooks] = useState(notebooks);
  const [selectedInfoNotebook, setSelectedInfoNotebook] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const { t } = useTranslation(["datasets", "common"]);

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

  const handleNotebookInfo = (notebookId) => {
    const notebook = notebooks.find((n) => n.id === notebookId);
    if (notebook) {
      setSelectedInfoNotebook(notebook);
    }
  };

  const getDatasetDescription = (dataset) => {
    return (
      dataset.description ||
      `${dataset.total_rows} ${t("common:rows")}, ${dataset.total_columns} ${t(
        "common:columns",
      )}`
    );
  };

  const getNotebookDescription = (notebook) => {
    if (notebook.dataset_id && datasets.length > 0) {
      const associatedDataset = datasets.find(
        (dataset) => dataset.id === notebook.dataset_id,
      );
      return associatedDataset?.name
        ? t("datasets:label.fromDataset", {
            datasetName: associatedDataset.name,
          })
        : t("datasets:label.noDataset");
    }
    return notebook.description || "";
  };

  const onDatasetClick = (id) => {
    selectDataset(id);
    clearSelectedNotebook();
    setStep(0);
    setSelectedOption("dataset");
  };

  const onNotebookClick = (id) => {
    selectNotebook(id);
    clearSelectedDataset();
    setStep(0);
    setSelectedOption("notebook");
  };

  const onDatasetDelete = async (id) => {
    if (id === selectedDatasetId) {
      clearSelectedDataset();
      setStep(0);
      setSelectedOption(null);
    }

    deleteDatasetLocal(id);
    removeNotebooksByDatasetId(id);
    await deleteDatasetRemote(id);
  };

  const onNotebookDelete = (id) => {
    deleteNotebookById(id);

    if (id === selectedNotebookId) {
      clearSelectedNotebook();
      setStep(0);
      setSelectedOption(null);
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
      <Divider sx={{ width: "100%", bgcolor: "divider" }} />

      {/* Create new item button */}
      <Box p={2} sx={{ height: "64px", display: "flex", alignItems: "center" }}>
        {selectedDatasetId || selectedNotebookId ? (
          <NewItemButton
            onClick={handleNewSessionButton}
            title={t("datasets:button.newDatasetNotebook")}
          />
        ) : (
          <Typography variant="body1" color="textSecondary">
            {t("datasets:label.datasetModule")}
          </Typography>
        )}
      </Box>

      {/* Search bar global */}
      <Box px={2} pb={2} flex={"0 0 auto"}>
        <SearchBar
          placeholder={t("datasets:label.searchDatasetsNotebooks")}
          value={searchQuery}
          onChange={handleSearchChange}
        />
      </Box>

      <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

      {/* Scrollable content */}
      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        <CollapsibleList
          items={filteredDatasets}
          selectedItemId={selectedDatasetId}
          onItemClick={onDatasetClick}
          onItemDelete={onDatasetDelete}
          onItemEdit={editDataset}
          defaultOpen={true}
          title={t("datasets:label.availableDatasets")}
          Icon={StorageIcon}
          getItemDescription={getDatasetDescription}
        />

        <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

        <CollapsibleList
          items={filteredNotebooks}
          selectedItemId={selectedNotebookId}
          onItemClick={onNotebookClick}
          onItemDelete={onNotebookDelete}
          onItemEdit={editNotebook}
          onItemInfo={handleNotebookInfo}
          defaultOpen={true}
          title={t("datasets:label.notebooks")}
          Icon={DescriptionIcon}
          datasets={datasets}
          getItemDescription={getNotebookDescription}
        />
      </Box>

      {/* Footer */}
      <Footer />

      {/* Notebook Info Modal */}
      {selectedInfoNotebook && (
        <InfoNotebookModal
          notebookData={selectedInfoNotebook}
          datasets={datasets}
          open={!!selectedInfoNotebook}
          onClose={() => setSelectedInfoNotebook(null)}
        />
      )}
    </SideBar>
  );
}
