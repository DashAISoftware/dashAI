import { useState, useEffect, useCallback } from "react";
import { useSnackbar } from "notistack";
import { startJobPolling } from "../../../utils/jobPoller";
import { enqueueDatasetJob } from "../../../api/job";
import {
  Box,
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Typography,
  Button,
  IconButton,
  CircularProgress,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Add } from "@mui/icons-material";
import HistoryIcon from "@mui/icons-material/History";
import { SaveDatasetModal } from "../datasetCreation/SaveDatasetModal";
import { getConvertersByNotebookId } from "../../../api/notebook";
import { getDatasetFile } from "../../../api/datasets";
import DatasetTable from "../dataset/DatasetTable";
import { NotebookHistoryModal } from "./NotebookHistoryModal";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";

const EMPTY_ARRAY = [];

export default function DatasetPreviewNotebook({
  notebook,
  existingDatasets = EMPTY_ARRAY,
  onAccordionChange,
}) {
  const { t } = useTranslation(["datasets", "common"]);

  const { enqueueSnackbar } = useSnackbar();

  const {
    datasets,
    createDataset,
    fetchDatasets,
    selectDataset,
    clearSelectedDataset,
    deleteDataset,
    enrichDatasetsWithInfo,
    replaceDatasets,
    setStep,
    setSelectedOption,
  } = useDatasetsAndNotebooks();

  const theme = useTheme();
  const [showSaveDatasetModal, setShowSaveDatasetModal] = useState(false);
  const [showNotebookHistoryModal, setShowNotebookHistoryModal] =
    useState(false);
  const [converters, setConverters] = useState([]);
  const { explorersAndConverters } = useExplorersAndConverters();
  const tourContext = useTourContext();

  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(notebook?.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [notebook, converters],
  );

  useEffect(() => {
    if (!notebook) return;
    let intervalId;

    const fetchConverters = async () => {
      try {
        const response = await getConvertersByNotebookId(notebook.id);
        setConverters(response);

        const isPollingNeeded = response.some(
          (converter) => converter.status < 3,
        );

        if (isPollingNeeded) {
          if (!intervalId) {
            intervalId = setInterval(fetchConverters, 2000);
          }
        } else {
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Error fetching converters:", error);
        clearInterval(intervalId);
      }
    };

    fetchConverters();

    return () => {
      clearInterval(intervalId);
    };
  }, [notebook, explorersAndConverters]);

  if (!notebook) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <CircularProgress color="primary" />
        <Typography>{t("common:loading")}...</Typography>
      </Box>
    );
  }

  const getDatasetName = () => {
    if (!notebook.dataset_id || !existingDatasets.length) {
      return "Dataset";
    }
    const dataset = existingDatasets.find((d) => d.id === notebook.dataset_id);
    return dataset ? dataset.name : "Dataset";
  };

  const pollForDataset = ({ datasetId, datasetName }, { jobId }) => {
    if (!jobId) return;

    startJobPolling(
      jobId,

      //Success
      async () => {
        enqueueSnackbar(
          t("datasets:message.datasetCreationSuccess", { datasetName }),
          { variant: "success" },
        );

        try {
          const freshDatasets = await fetchDatasets(true);
          const dataset = freshDatasets.find((d) => d.id === datasetId);

          if (dataset) {
            const enriched = await enrichDatasetsWithInfo(
              freshDatasets,
              datasets,
            );
            replaceDatasets(enriched);
            selectDataset(datasetId);
            setStep(0);
            setSelectedOption("dataset");
          } else {
            await fetchDatasets();
            selectDataset(datasetId);
            setStep(0);
            setSelectedOption("dataset");
          }
        } catch (error) {
          console.error("Error after dataset job completion:", error);
          await fetchDatasets();
          selectDataset(datasetId);
          setStep(0);
          setSelectedOption("dataset");
        }
      },

      //Failure
      async (result) => {
        console.error("Dataset job failed:", result);

        enqueueSnackbar(
          t("datasets:error.failedToCreateDataset", {
            error: result?.error || t("common:unknownError"),
          }),
          { variant: "error" },
        );

        try {
          await deleteDataset(datasetId);
        } catch (e) {
          console.error(e);
        }
        clearSelectedDataset();
        setStep(0);
        setSelectedOption(null);
      },
    );
  };

  const handleAddDatasetFromNotebook = async (name, notebookId) => {
    try {
      console.log(
        "Creating dataset from notebook:",
        notebookId,
        "with name:",
        name,
      );
      const dataset = await createDataset(name);

      enqueueSnackbar(t("datasets:message.datasetCreationStarted"), {
        variant: "success",
      });

      // optimistic
      replaceDatasets((prev) => [...prev, dataset]);
      selectDataset(dataset.id);
      setStep(0);
      setSelectedOption("dataset");

      const job = await enqueueDatasetJob(dataset.id, null, "", {}, notebookId);

      pollForDataset(
        { datasetId: dataset.id, datasetName: name },
        { jobId: job.id },
      );
    } catch (error) {
      enqueueSnackbar(t("datasets:error.failedToCreateDatasetFromNotebook"), {
        variant: "error",
      });
      console.error("Failed to create dataset from notebook:", error);
    }
  };

  return (
    <Box>
      <Accordion
        data-tour="dataset-preview-section"
        sx={{
          bgcolor: theme.palette.ui.box,
          borderRadius: 2,
          boxShadow: "none",
        }}
        defaultExpanded={true}
        onChange={(event, expanded) => {
          if (onAccordionChange) {
            onAccordionChange(expanded);
          }
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            transition: "background-color 0.2s ease",
            "&:hover": {
              bgcolor: "rgba(255, 255, 255, 0.05)",
            },
            "& .MuiAccordionSummary-content": {
              flexGrow: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              margin: "0px 0 !important",
            },
          }}
        >
          <Typography variant="h6">
            {t("datasets:label.datasetPreviewFor", { name: getDatasetName() })}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Button
              variant="contained"
              size="small"
              endIcon={<Add />}
              onClick={(e) => {
                e.stopPropagation();
                setShowSaveDatasetModal(true);
                if (tourContext && tourContext.run) {
                  setTimeout(() => {
                    tourContext.nextStep();
                  }, 500);
                }
              }}
              sx={{
                fontSize: "0.7rem",
                px: 1.5,
                py: 0.5,
                textTransform: "uppercase",
                minWidth: "auto",
              }}
              className="save-dataset-button"
            >
              {t("datasets:button.saveAsNewDataset")}
            </Button>
            <IconButton
              size="small"
              sx={{ color: "primary.main", ml: 1 }}
              onClick={(e) => {
                e.stopPropagation();
                setShowNotebookHistoryModal(true);
              }}
            >
              <HistoryIcon />
            </IconButton>
          </Box>
        </AccordionSummary>

        <AccordionDetails>
          <Box sx={{ width: "100%" }}>
            <DatasetTable
              fetchPage={fetchDatasetPage}
              deps={[notebook.file_path, converters, explorersAndConverters]}
              initialPageSize={5}
              density="compact"
              datasetPath={notebook.file_path}
              pageSizeOptions={[5, 10, 25]}
              autoHeight={true}
              disableColumnSelector
              disableDensitySelector
              sx={{
                "& .MuiTablePagination-select": {
                  display: "none",
                },
                "& .MuiTablePagination-selectLabel": {
                  display: "none",
                },
              }}
            />
          </Box>
        </AccordionDetails>
      </Accordion>

      <SaveDatasetModal
        open={showSaveDatasetModal}
        onClose={() => setShowSaveDatasetModal(false)}
        onSaveDataset={(name) =>
          handleAddDatasetFromNotebook(name, notebook.id)
        }
        appliedConverters={converters.filter(
          (converter) => converter.status === 3,
        )}
        existingDatasets={existingDatasets}
      />

      <NotebookHistoryModal
        open={showNotebookHistoryModal}
        onClose={() => setShowNotebookHistoryModal(false)}
        notebook={notebook}
        converters={converters.filter((converter) => converter.status === 3)}
      />
    </Box>
  );
}
