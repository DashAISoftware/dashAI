import React, { useState, useCallback, useEffect } from "react";
import { useSnackbar } from "notistack";
import CustomLayout from "../../components/custom/CustomLayout";
import PredictionTable from "../../components/predictions/PredictionTable";
import PredictionModal from "../../components/predictions/PredictionModal";
import { useLocation } from "react-router-dom";
import { get_metadata_prediction_json } from "../../api/predict";

function PredictionPage() {
  const location = useLocation();
  const [selection, setSelection] = useState(() => ({
    modelId: location.state?.runId,
    trainedDatasetId: location.state?.trainedDatasetId,
  }));
  const [loading, setLoading] = useState(true);

  const setModelId = useCallback((id) => {
    setSelection((prev) => ({ ...prev, modelId: id }));
  }, []);

  const setTrainedDatasetId = useCallback((id) => {
    setSelection((prev) => ({ ...prev, trainedDatasetId: id }));
  }, []);

  const { modelId, trainedDatasetId } = selection;
  console.log("trainedDatasetId", trainedDatasetId);

  const [updateTableFlag, setUpdateTableFlag] = useState(false);
  const [isNewPredictionModalOpen, setIsNewPredictionModalOpen] = useState(
    !!modelId,
  );
  const [predictions, setPredictions] = useState([]);
  const { enqueueSnackbar } = useSnackbar();

  const getPredictions = async () => {
    try {
      setLoading(true);
      console.log("Fetching predictions...", predictions);
      const predictionsData = await get_metadata_prediction_json();
      setPredictions(predictionsData);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain predictions.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenNewPredictionModal = async () => {
    setIsNewPredictionModalOpen(true);
  };

  useEffect(() => {
    getPredictions();
  }, []);

  useEffect(() => {
    if (updateTableFlag) {
      setUpdateTableFlag(false);
      getPredictions();
    }
  }, [updateTableFlag]);

  return (
    <CustomLayout
      title="Prediction Module"
      subtitle="Use a model to make predictions"
    >
      <PredictionTable
        updateTableFlag={updateTableFlag}
        setUpdateTableFlag={setUpdateTableFlag}
        handleNewPredict={handleOpenNewPredictionModal}
        predictions={predictions}
      />

      {!loading && (
        <PredictionModal
          open={isNewPredictionModalOpen}
          onClose={() => setIsNewPredictionModalOpen(false)}
          updatePredictions={() => setUpdateTableFlag(true)}
          preselectedModelId={modelId}
          setPreselectedModelId={setModelId}
          preselectedTrainedDatasetId={trainedDatasetId}
          setPreselectedTrainedDatasetId={setTrainedDatasetId}
          existingPredictions={predictions}
        />
      )}
    </CustomLayout>
  );
}

export default PredictionPage;
