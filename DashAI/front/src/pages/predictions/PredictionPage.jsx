import React, { useState, useCallback } from "react";
import CustomLayout from "../../components/custom/CustomLayout";
import PredictionTable from "../../components/predictions/PredictionTable";
import PredictionModal from "../../components/predictions/PredictionModal";
import useJobPolling from "../../hooks/useJobPolling";
import JobQueueWidget from "../../components/jobs/JobQueueWidget";

function PredictionPage() {
  const [updateTableFlag, setUpdateTableFlag] = useState(false);
  const [isNewPredictionModalOpen, setIsNewPredictionModalOpen] =
    useState(false);

  const bumpTable = useCallback(() => {
    setUpdateTableFlag((v) => !v);
  }, []);

  const handleJobsUpdated = useCallback(() => {
    bumpTable();
  }, [bumpTable]);

  useJobPolling(3000, handleJobsUpdated, ["started", "finished", "error"]);

  return (
    <>
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
          updatePredictions={bumpTable}
        />
      </CustomLayout>

      {/* Add the JobQueueWidget */}
      <JobQueueWidget />
    </>
  );
}

export default PredictionPage;
