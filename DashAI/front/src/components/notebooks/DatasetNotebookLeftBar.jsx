import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Divider, Typography } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import DescriptionIcon from "@mui/icons-material/Description";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import Footer from "../threeSectionLayout/Footer";
import CollapsibleList from "../threeSectionLayout/CollapsibleList";
import SearchBar from "../threeSectionLayout/SearchBar";
import NewItemButton from "../threeSectionLayout/NewItemButton";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import InfoNotebookModal from "./notebook/InfoNotebookModal";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";

import { useDatasetsAndNotebooks } from "../custom/contexts/DatasetsAndNotebooksContext";
import { listDatafiles, deleteDatafile } from "../../api/hub";
import { subscribeJobs } from "../../utils/jobPoller";

export default function DatasetsNotebooksLeftBar({
  onToggle,
  onDownloadDelete,
}) {
  const {
    datasets,
    notebooks,
    selectedDatasetId,
    selectedNotebookId,
    deleteDatasetById,
    removeNotebooksByDatasetId,
    editDataset,
    editNotebook,
    deleteNotebookById,
  } = useDatasetsAndNotebooks();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();

  const [filteredDatasets, setFilteredDatasets] = useState(datasets);
  const [filteredNotebooks, setFilteredNotebooks] = useState(notebooks);
  const [filteredDownloads, setFilteredDownloads] = useState([]);
  const [downloads, setDownloads] = useState([]);
  const [selectedInfoNotebook, setSelectedInfoNotebook] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const { t } = useTranslation(["datasets", "common", "hub"]);

  useEffect(() => {
    listDatafiles()
      .then(setDownloads)
      .catch(() => {});
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeJobs((jobs) => {
      if (Array.isArray(jobs) && jobs.some((j) => j.status === "finished")) {
        listDatafiles()
          .then(setDownloads)
          .catch(() => {});
      }
    });
    return unsubscribe;
  }, []);

  const SEARCH_THRESHOLD = 10;
  const totalItems = datasets.length + notebooks.length + downloads.length;

  useEffect(() => {
    if (totalItems <= SEARCH_THRESHOLD) setSearchQuery("");
  }, [totalItems]);

  useEffect(() => {
    const q = searchQuery.trim().toLowerCase();

    if (!q) {
      setFilteredDatasets(datasets);
      setFilteredNotebooks(notebooks);
      setFilteredDownloads(downloads);
      return;
    }

    const match = (item) => (item?.name ?? "").toLowerCase().includes(q);

    setFilteredDatasets(datasets.filter(match));
    setFilteredNotebooks(notebooks.filter(match));
    setFilteredDownloads(downloads.filter(match));
  }, [searchQuery, datasets, notebooks, downloads]);

  const handleSearchChange = (e) => setSearchQuery(e.target.value);

  const handleNotebookInfo = (notebookId) => {
    const notebook = notebooks.find((n) => n.id === notebookId);
    if (notebook) {
      setSelectedInfoNotebook(notebook);
    }
  };

  const handleDeleteDownload = async (id) => {
    const name = downloads.find((d) => d.id === id)?.name ?? "";
    try {
      await deleteDatafile(id);
      setDownloads((prev) => prev.filter((d) => d.id !== id));
      enqueueSnackbar(t("hub:deleteSuccess", { name }), { variant: "success" });
      onDownloadDelete?.(id);
    } catch {
      enqueueSnackbar(t("hub:deleteError"), { variant: "error" });
    }
  };

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

  const getNotebookDeleteConfirmationContent = (notebook) =>
    t(
      "datasets:label.confirmDeleteNotebook",
      'Are you sure you want to delete the notebook "{{name}}"? This action cannot be undone.',
      { name: notebook.name },
    );

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
    navigate(`/app/data/datasets/${id}`);
  };

  const onNotebookClick = (id) => {
    navigate(`/app/data/notebooks/${id}`);
  };

  const onDatasetDelete = async (id) => {
    const success = await deleteDatasetById(id);
    if (!success) return;
    if (id === selectedDatasetId) {
      navigate("/app/data");
    }
    removeNotebooksByDatasetId(id);
  };

  const onNotebookDelete = async (id) => {
    const success = await deleteNotebookById(id);
    if (!success) return;
    if (id === selectedNotebookId) {
      navigate("/app/data");
    }
  };

  const handleNewSessionButton = () => {
    navigate("/app/data");
  };

  return (
    <SideBar>
      {/* Create new item button */}
      <Box p={4} sx={{ height: "64px", display: "flex", alignItems: "center" }}>
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
      {totalItems > SEARCH_THRESHOLD && (
        <Box px={4} pb={4} flex={"0 0 auto"}>
          <SearchBar
            placeholder={t("datasets:label.searchDatasetsNotebooks")}
            value={searchQuery}
            onChange={handleSearchChange}
          />
        </Box>
      )}

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
          getDeleteConfirmationContent={getDatasetDeleteConfirmationContent}
          getDeleteConfirmationWarning={getDatasetDeleteConfirmationWarning}
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
          getDeleteConfirmationContent={getNotebookDeleteConfirmationContent}
        />

        <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

        <CollapsibleList
          items={filteredDownloads}
          onItemClick={(id) => {
            const dl = filteredDownloads.find((d) => d.id === id);
            if (dl?.status === "ready")
              navigate(`/app/data/hub/import/${dl.id}`);
          }}
          onItemDelete={handleDeleteDownload}
          onItemEdit={() => {}}
          defaultOpen={true}
          title={t("hub:downloadedDatasets")}
          Icon={CloudDownloadIcon}
          getItemDescription={(dl) =>
            t("hub:fromSource", { source: dl.source_name })
          }
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
