import { useState, useEffect } from "react";
import { useSnackbar } from "notistack";

import NewExperimentModal from "../../components/experiments/NewExperimentModal";
import ExperimentsTable from "../../components/experiments/ExperimentsTable";
import CustomLayout from "../../components/custom/CustomLayout";
import { getExperiments as getExperimentsRequest } from "../../api/experiment";
import { getDatasets } from "../../api/datasets";

function ExperimentsPage() {
  const [showNewExperimentModal, setShowNewExperimentModal] = useState(false);
  const [updateTableFlag, setUpdateTableFlag] = useState(false);
  const [experiments, setExperiments] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();

  const getExperiments = async () => {
    setLoading(true);
    try {
      const experimentsData = await getExperimentsRequest();
      setExperiments(experimentsData);
    } catch (error) {
      enqueueSnackbar("Error while trying to get experiments.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDatasets = async () => {
    try {
      const datasetsData = await getDatasets();
      setDatasets(datasetsData);
    } catch (error) {
      enqueueSnackbar("Error while trying to get datasets.");
      console.error(error);
    }
  };

  useEffect(() => {
    getExperiments();
    fetchDatasets();
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
      <NewExperimentModal
        open={showNewExperimentModal}
        setOpen={setShowNewExperimentModal}
        updateExperiments={() => setUpdateTableFlag(true)}
        existingExperiments={experiments}
      />

      {/* Experiment table */}
      <ExperimentsTable
        handleOpenNewExperimentModal={() => setShowNewExperimentModal(true)}
        updateTableFlag={updateTableFlag}
        setUpdateTableFlag={setUpdateTableFlag}
        experiments={experiments}
        datasets={datasets}
        loading={loading}
        onUpdateExperiments={getExperiments}
      />
    </CustomLayout>
  );
}

export default ExperimentsPage;
