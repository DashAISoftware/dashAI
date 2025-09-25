import React, { useState, useCallback, useEffect } from "react";
import { useSnackbar } from "notistack";
import CustomLayout from "../../components/custom/CustomLayout";
import PredictionTable from "../../components/predictions/PredictionTable";
import PredictionModal from "../../components/predictions/PredictionModal";
import { get_metadata_prediction_json } from "../../api/predict";

function PredictionPage() {
  const [updateTableFlag, setUpdateTableFlag] = useState(false);
  const [isNewPredictionModalOpen, setIsNewPredictionModalOpen] =
    useState(false);
  const [predictions, setPredictions] = useState([]);
  const { enqueueSnackbar } = useSnackbar();

  const getPredictions = async () => {
    try {
      const predictionsData = await get_metadata_prediction_json();
      setPredictions(predictionsData);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain predictions.");
      console.error(error);
    }
  };

  const updatePredictions = useCallback(() => {
    setUpdateTableFlag(true);
    getPredictions();
  }, []);

  const handleOpenNewPredictionModal = async () => {
    await getPredictions();
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

      <PredictionModal
        open={isNewPredictionModalOpen}
        onClose={() => setIsNewPredictionModalOpen(false)}
        updatePredictions={updatePredictions}
        existingPredictions={predictions}
      />
    </CustomLayout>
  );
}

export default PredictionPage;
