import { useState, useEffect, useCallback } from "react";
import { useSnackbar } from "notistack";

import NewExperimentModal from "../../components/experiments/NewExperimentModal";
import ExperimentsTable from "../../components/experiments/ExperimentsTable";
import CustomLayout from "../../components/custom/CustomLayout";
import { useLocation } from "react-router-dom";
import { getExperiments as getExperimentsRequest } from "../../api/experiment";

function ExperimentsPage() {
  const location = useLocation();
  const [dataset, setDataset] = useState(location.state?.dataset);
  const [showNewExperimentModal, setShowNewExperimentModal] =
    useState(!!dataset);
  const [updateTableFlag, setUpdateTableFlag] = useState(false);
  const [experiments, setExperiments] = useState([]);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();

  const getExperiments = async () => {
    setLoading(true);
    try {
      const experimentsData = await getExperimentsRequest();
      setExperiments(experimentsData);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain experiments.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getExperiments();
  }, []);

  // Update experiments when table is updated
  useEffect(() => {
    if (updateTableFlag) {
      setUpdateTableFlag(false);
      getExperiments();
    }
  }, [updateTableFlag]);

  return (
    <CustomLayout
      title="Experiments Module"
      subtitle="Configure experiments to train models"
    >
      {/* New experiment Modal */}
      {!loading && (
        <NewExperimentModal
          open={showNewExperimentModal}
          setOpen={setShowNewExperimentModal}
          updateExperiments={() => setUpdateTableFlag(true)}
          preselectedDataset={dataset}
          setPreselectedDataset={setDataset}
          existingExperiments={experiments}
        />
      )}

      {/* Experiment table */}
      <ExperimentsTable
        handleOpenNewExperimentModal={() => setShowNewExperimentModal(true)}
        updateTableFlag={updateTableFlag}
        setUpdateTableFlag={setUpdateTableFlag}
        experiments={experiments}
        loading={loading}
        onUpdateExperiments={getExperiments}
      />
    </CustomLayout>
  );
}

export default ExperimentsPage;
