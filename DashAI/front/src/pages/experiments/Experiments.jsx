import React from "react";

import NewExperimentModal from "../../components/experiments/NewExperimentModal";
import ExperimentsTable from "../../components/experiments/ExperimentsTable";
import { rows } from "../../example_data/experiments";
import CustomLayout from "../../components/custom/CustomLayout";
import { useLocation } from "react-router-dom";

function ExperimentsPage() {
  const [updateTableFlag, setUpdateTableFlag] = React.useState(false);
  const location = useLocation();
  const [dataset, setDataset] = React.useState(location.state?.dataset);
  const [showNewExperimentModal, setShowNewExperimentModal] = React.useState(
    !!dataset,
  );

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
        preselectedDataset={dataset}
        setPreselectedDataset={setDataset}
      />

      {/* Experiment table */}
      <ExperimentsTable
        initialRows={rows}
        handleOpenNewExperimentModal={() => setShowNewExperimentModal(true)}
        updateTableFlag={updateTableFlag}
        setUpdateTableFlag={setUpdateTableFlag}
      />
    </CustomLayout>
  );
}

ExperimentsPage.propTypes = {};

export default ExperimentsPage;
