import React, { useState, useCallback } from "react";
import CustomLayout from "../../components/custom/CustomLayout";
import PredictionTable from "../../components/predictions/PredictionTable";
import PredictionModal from "../../components/predictions/PredictionModal";
import { useLocation } from "react-router-dom";

function PredictionPage() {
  const location = useLocation();
  const [selection, setSelection] = useState(() => ({
    modelId: location.state?.runId,
    trainedDatasetId: location.state?.trainedDatasetId,
  }));

  const setModelId = useCallback((id) => {
    setSelection((prev) => ({ ...prev, modelId: id }));
  }, []);

  const setTrainedDatasetId = useCallback((id) => {
    setSelection((prev) => ({ ...prev, trainedDatasetId: id }));
  }, []);

  const { modelId, trainedDatasetId } = selection;

  const [updateTableFlag, setUpdateTableFlag] = useState(false);
  const [isNewPredictionModalOpen, setIsNewPredictionModalOpen] = useState(
    modelId ? true : false,
  );

  const updatePredictions = useCallback(() => {
    setUpdateTableFlag(true);
  }, []);

  return (
    <CustomLayout
      title="Prediction Module"
      subtitle="Use a model to make predictions"
    >
      <PredictionTable
        updateTableFlag={updateTableFlag}
        setUpdateTableFlag={setUpdateTableFlag}
        handleNewPredict={() => setIsNewPredictionModalOpen(true)}
      />

      <PredictionModal
        open={isNewPredictionModalOpen}
        onClose={() => setIsNewPredictionModalOpen(false)}
        updatePredictions={updatePredictions}
        preselectedModelId={modelId}
        setPreselectedModelId={setModelId}
        preselectedTrainedDatasetId={trainedDatasetId}
        setPreselectedTrainedDatasetId={setTrainedDatasetId}
      />
    </CustomLayout>
  );
}

export default PredictionPage;
