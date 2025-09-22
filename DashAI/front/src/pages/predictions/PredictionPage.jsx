import React, { useState, useCallback } from "react";
import CustomLayout from "../../components/custom/CustomLayout";
import PredictionTable from "../../components/predictions/PredictionTable";
import PredictionModal from "../../components/predictions/PredictionModal";

function PredictionPage() {
  const [updateTableFlag, setUpdateTableFlag] = useState(false);
  const [isNewPredictionModalOpen, setIsNewPredictionModalOpen] =
    useState(false);

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
      />
    </CustomLayout>
  );
}

export default PredictionPage;
