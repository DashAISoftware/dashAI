import { useState, useRef, useEffect } from "react";
import SelectDataloaderStep from "./SelectDataloaderStep";
import ConfigureAndUploadDatasetStep from "./ConfigureAndUploadDatasetStep";
import DataloaderConfigBar from "./DataloaderConfigBar";
import CustomLayout from "../../custom/CustomLayout";

export default function UploadDatasetSteps({
  backHome,
  handleDatasetCreated,
  existingDatasets = [],
  renderRightBar,
}) {
  const [step, setStep] = useState(0);
  const [selectedDataloader, setSelectedDataloader] = useState({});
  const [formValues, setFormValues] = useState({});
  const [error, setError] = useState(false);
  const [previewError, setPreviewError] = useState(false);

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
        return "Select a way to upload your data";
      case 1:
        return "Upload your dataset and configure parameters";
      default:
        return "Configure your dataset";
    }
  };

  // Update the right sidebar based on current step
  useEffect(() => {
    if (renderRightBar) {
      if (step === 1 && Object.entries(selectedDataloader).length !== 0) {
        renderRightBar(
          <DataloaderConfigBar
            selectedDataloader={selectedDataloader.name}
            formSubmitRef={formSubmitRef}
            setError={setError}
            existingDatasets={existingDatasets}
            onValuesChange={setFormValues}
          />,
        );
      } else {
        renderRightBar(null);
      }
    }
  }, [step, selectedDataloader, existingDatasets, renderRightBar]);

  return (
    <CustomLayout title={"Upload Dataset"} subtitle={getSubtitle()} padding={0}>
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
