import { useState } from "react";
import SelectDataloaderStep from "./SelectDataloaderStep";
import ConfigureAndUploadDatasetStep from "./ConfigureAndUploadDatasetStep";
import CustomLayout from "../../custom/CustomLayout";

export default function UploadDatasetSteps({
  backHome,
  handleDatasetCreated,
  existingDatasets = [],
}) {
  const [step, setStep] = useState(0);
  const [selectedDataloader, setSelectedDataloader] = useState({});

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

  return (
    <CustomLayout
      title={"Upload Dataset"}
      subtitle={
        step === 0
          ? "Select a way to upload your data"
          : "Configure your dataset"
      }
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
          existingDatasets={existingDatasets}
        />
      )}
    </CustomLayout>
  );
}
