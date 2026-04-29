import { useState, useRef, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import SelectDataloaderStep from "./SelectDataloaderStep";
import ConfigureAndUploadDatasetStep from "./ConfigureAndUploadDatasetStep";
import DataloaderConfigBar from "./DataloaderConfigBar";
import CustomLayout from "../../custom/CustomLayout";
import { useTranslation } from "react-i18next";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";
import { useTourContext } from "../../tour/TourProvider";

const UPLOAD_BASE_PATH = "/app/data/datasets/new";
const UPLOAD_CONFIGURE_PATH = `${UPLOAD_BASE_PATH}/configure`;

export default function UploadDatasetSteps({ backHome }) {
  const {
    datasets,
    addDatasetOptimistically,
    startDatasetPolling,
    setRightBarContent,
  } = useDatasetsAndNotebooks();

  const navigate = useNavigate();
  const location = useLocation();
  const step = location.pathname.startsWith(UPLOAD_CONFIGURE_PATH) ? 1 : 0;
  const [selectedDataloader, setSelectedDataloader] = useState({});
  const [formValues, setFormValues] = useState({});
  const [error, setError] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const { t } = useTranslation(["datasets"]);
  const tourContext = useTourContext();

  const formSubmitRef = useRef(null);

  const goToNextStep = () => {
    navigate(UPLOAD_CONFIGURE_PATH);
  };

  const goToPrevStep = () => {
    if (step === 0) {
      backHome();
      return;
    }

    navigate(UPLOAD_BASE_PATH);
  };

  const getSubtitle = () => {
    switch (step) {
      case 0:
        return t("datasets:label.selectUploadMethod");
      case 1:
        return t("datasets:label.uploadAndConfigure");
      default:
        return t("datasets:label.configureDataset");
    }
  };

  useEffect(() => {
    if (step === 1 && Object.keys(selectedDataloader).length === 0) {
      navigate(UPLOAD_BASE_PATH, { replace: true });
    }
  }, [step, selectedDataloader, navigate]);

  // Update the right sidebar based on current step
  useEffect(() => {
    if (setRightBarContent) {
      if (step === 1 && Object.entries(selectedDataloader).length !== 0) {
        setRightBarContent(
          <DataloaderConfigBar
            selectedDataloader={selectedDataloader.name}
            formSubmitRef={formSubmitRef}
            setError={setError}
            existingDatasets={datasets}
            onValuesChange={setFormValues}
          />,
        );
      } else {
        setRightBarContent(null);
      }
    }
  }, [step, selectedDataloader, datasets, setRightBarContent]);

  const handleDatasetCreated = (newDataset, datasetJob) => {
    addDatasetOptimistically(newDataset);
    setRightBarContent(null);
    startDatasetPolling(newDataset, datasetJob);
    navigate(`/app/data/datasets/${newDataset.id}`);

    if (tourContext?.run) {
      tourContext.stopTour();
      sessionStorage.setItem("startDatasetViewTour", "true");
    }
  };

  return (
    <CustomLayout
      title={t("datasets:label.uploadDataset")}
      subtitle={getSubtitle()}
      padding={0}
    >
      {step === 0 && (
        <SelectDataloaderStep
          goToNextStep={goToNextStep}
          goToPrevStep={goToPrevStep}
          selectedDataloader={selectedDataloader}
          setSelectedDataloader={setSelectedDataloader}
        />
      )}
      {step === 1 && Object.entries(selectedDataloader).length !== 0 && (
        <ConfigureAndUploadDatasetStep
          goToPrevStep={goToPrevStep}
          selectedDataloader={selectedDataloader}
          backHome={backHome}
          handleDatasetCreated={handleDatasetCreated}
          formSubmitRef={formSubmitRef}
          formValues={formValues}
          onPreviewError={setPreviewError}
          formHasErrors={error}
        />
      )}
    </CustomLayout>
  );
}
