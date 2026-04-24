import { useCallback, useEffect } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import NotebookVisualization from "../notebook/NotebookVisualization";
import UploadDatasetSteps from "../datasetCreation/UploadDatasetSteps";
import UploadNotebookSteps from "../notebookCreation/UploadNotebookSteps";
import DatasetVisualization from "../../DatasetVisualization";
import SelectOptionMenu from "../../threeSectionLayout/SelectOptionMenu";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";
import {
  CloudUpload as UploadDatasetIcon,
  AutoStories as NotebookIcon,
} from "@mui/icons-material";

export default function DatasetsCenterContent() {
  const {
    datasets,
    notebooks,
    selectedDatasetId,
    selectedNotebookId,
    setRightBarContent,
    step,
    fetchDatasets,
    fetchNotebooks,
    selectedOption,
  } = useDatasetsAndNotebooks();

  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets", "common"]);
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const preselectedDatasetIdFromState =
    location.state?.preselectedDatasetId ?? null;

  useEffect(() => {
    if (searchParams.get("action") === "upload") {
      searchParams.delete("action");
      setSearchParams(searchParams, { replace: true });
      navigate("/app/data/upload/dataset");
    }
  }, [searchParams]);

  const selectedDataset = datasets.find((n) => n.id === selectedDatasetId);
  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  const goToNextStep = useCallback(
    (option) => {
      if (option === "dataset") {
        navigate("/app/data/upload/dataset");
        if (tourContext?.run) {
          setTimeout(() => {
            tourContext.nextStep();
          }, 600);
        }
        return;
      }

      navigate("/app/data/upload/notebook");
    },
    [tourContext, navigate],
  );

  const handleNotebookCreated = async (createdNotebook) => {
    await fetchNotebooks();
    navigate(`/app/data/notebooks/${createdNotebook.id}`);
  };

  const handleNewNotebookFromDataset = () => {
    navigate("/app/data/upload/notebook", {
      state: { preselectedDatasetId: selectedDatasetId },
    });
  };

  if (selectedNotebookId && selectedOption === "notebook") {
    return (
      <NotebookVisualization
        notebook={selectedNotebook}
        existingDatasets={datasets}
      />
    );
  }

  if (selectedDatasetId && selectedOption === "dataset") {
    return (
      <DatasetVisualization
        dataset={selectedDataset}
        onNewItem={handleNewNotebookFromDataset}
        newItemButtonText={t("datasets:button.newNotebook")}
        tourContextType="datasets"
      />
    );
  }

  if (step === 1 && selectedOption === "dataset") {
    return (
      <UploadDatasetSteps
        backHome={() => {
          fetchDatasets();
          setRightBarContent(null);
          navigate("/app/data");
        }}
      />
    );
  }
  if (step === 1 && selectedOption === "notebook") {
    return (
      <UploadNotebookSteps
        backHome={() => {
          fetchNotebooks();
          navigate("/app/data");
        }}
        datasets={datasets}
        handleNotebookCreated={handleNotebookCreated}
        existingNotebooks={notebooks}
        preselectedDatasetId={preselectedDatasetIdFromState}
      />
    );
  }
  if (step === 0) {
    return (
      <SelectOptionMenu
        title={t("datasets:label.datasetModule")}
        subtitle={t("datasets:label.datasetModuleSubtitle")}
        options={[
          {
            name: "dataset",
            display_name: t("datasets:label.uploadDataset"),
            description: t("datasets:label.uploadDatasetDescription"),
            Icon: UploadDatasetIcon,
            "data-tour": "dataset-option",
          },
          {
            name: "notebook",
            display_name: t("datasets:label.createNewNotebook"),
            description: t("datasets:label.createNewNotebookDescription"),
            Icon: NotebookIcon,
            "data-tour": "notebook-option",
          },
        ]}
        searchBar={false}
        goToNextStep={goToNextStep}
      />
    );
  }
  return null;
}
