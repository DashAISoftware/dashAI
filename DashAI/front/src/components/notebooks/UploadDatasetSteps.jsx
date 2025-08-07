import React, { useState } from "react";
import SelectDataloaderStep from "../../components/notebooks/SelectDataloaderStep";
import ConfigureAndUploadDataset from "../../components/notebooks/ConfigureAndUploadDataset";

const defaultNewDataset = {
  dataloader: "",
  file: null,
  url: "",
  params: {},
};

export default function UploadDatasetSteps({ backHome }) {
  const [step, setStep] = React.useState(0);
  const [selectedDataloader, setSelectedDataloader] = useState({});
  const [newDataset, setNewDataset] = useState(defaultNewDataset);

  const goToNextStep = () => {
    setStep((prevStep) => prevStep + 1);
  };

  const goToPrevStep = () => {
    setStep((prevStep) => prevStep - 1);
  };

  return (
    <>
      {step === 0 && (
        <SelectDataloaderStep
          newDataset={newDataset}
          setNewDataset={setNewDataset}
          goToNextStep={goToNextStep}
          goToPrevStep={() => {
            goToPrevStep(null);
            backHome();
          }}
          selectedDataloader={selectedDataloader}
          setSelectedDataloader={setSelectedDataloader}
        />
      )}
      {step === 1 && Object.entries(selectedDataloader).length !== 0 && (
        <ConfigureAndUploadDataset
          newDataset={newDataset}
          setNewDataset={setNewDataset}
          goToNextStep={() => {
            setStep(0);
            setSelectedDataloader({});
            setNewDataset(defaultNewDataset);
          }}
          goToPrevStep={() => {
            goToPrevStep();
            setNewDataset(defaultNewDataset);
            setSelectedDataloader({});
          }}
          selectedDataloader={selectedDataloader}
          setSelectedDataloader={setSelectedDataloader}
          backHome={backHome}
        />
      )}
    </>
  );
}
