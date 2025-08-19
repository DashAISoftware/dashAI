import React from "react";

import CustomLayout from "../../components/custom/CustomLayout";
import { PipelinesTable } from "../../components/pipelines";

function PipelinesPage() {
  const [showNewPipeline, setShowNewPipeline] = React.useState(false);
  const [updateTableFlag, setUpdateTableFlag] = React.useState(false);

  return (
    <CustomLayout
      title="Pipelines Module"
      subtitle="Manage and visualize pipelines"
    >
      <PipelinesTable
        handleOpenNewPipeline={() => setShowNewPipeline(true)}
        updateTableFlag={updateTableFlag}
        setUpdateTableFlag={setUpdateTableFlag}
      />
    </CustomLayout>
  );
}

export default PipelinesPage;
