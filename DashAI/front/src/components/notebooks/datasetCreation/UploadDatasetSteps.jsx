import { useState, useRef, useEffect } from "react";
import SelectDataloaderStep from "./SelectDataloaderStep";
import ConfigureAndUploadDatasetStep from "./ConfigureAndUploadDatasetStep";
import DataloaderConfigBar from "./DataloaderConfigBar";
import CustomLayout from "../../custom/CustomLayout";
import { useTranslation } from "react-i18next";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";

export default function UploadDatasetSteps({ backHome }) {
  const {
    datasets,
    addDatasetOptimistically,
    setStep: setGlobalStep,
    setSelectedOption,
    clearSelectedNotebook,
    startDatasetPolling,
    setRightBarContent,
  } = useDatasetsAndNotebooks();

  const [step, setStep] = useState(0);
  const [selectedDataloader, setSelectedDataloader] = useState({});
  const [formValues, setFormValues] = useState({});
  const [error, setError] = useState(false);
  const [previewError, setPreviewError] = useState(false);
  const { t } = useTranslation(["datasets"]);

  const formSubmitRef = useRef(null);

  const goToNextStep = () => {
    setStep((prevStep) => prevStep + 1);
  };

  const goToPrevStep = () => {
    if (step === 0) {
      backHome();
      return;
    }

    setStep((prevStep) => prevStep - 1);
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
    setGlobalStep(0);
    setSelectedOption("dataset");
    clearSelectedNotebook();
    setRightBarContent(null);
    startDatasetPolling(newDataset, datasetJob);
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
