import React, { useState, useCallback, useRef } from "react";
import DatasetsTable from "../../components/datasets/DatasetsTable";
import DatasetModal from "../../components/datasets/DatasetModal";
import CustomLayout from "../../components/custom/CustomLayout";
import useJobPolling, {
  checkQueueAndMaybeStartPolling,
} from "../../hooks/useJobPolling";
import JobQueueWidget from "../../components/jobs/JobQueueWidget";

function DatasetsPage() {
  const [open, setOpen] = useState(false);
  const [updateTableFlag, setUpdateTableFlag] = useState(false);

  const bumpTable = useCallback(() => {
    setUpdateTableFlag((v) => !v);
  }, []);

  const lastBumpRef = useRef(0);
  const throttleBump = useCallback(() => {
    const now = Date.now();
    if (now - lastBumpRef.current > 400) {
      lastBumpRef.current = now;
      bumpTable();
    }
  }, [bumpTable]);

  const handleJobsUpdated = useCallback(
    (changes, meta) => {
      console.debug("[Datasets poll]", {
        changesLen: Array.isArray(changes) ? changes.length : 0,
        meta,
        sample: Array.isArray(changes)
          ? changes.slice(0, 3).map((c) => ({
              id: c.id ?? c.job_id,
              status: c.status ?? c.state,
              last_update: c.last_update ?? c.updated_at,
              task_type: c.task_type ?? c.task,
            }))
          : [],
      });

      const hasChanges = Array.isArray(changes) && changes.length > 0;
      const justCompleted = !!meta?.recentlyCompleted;

      if (hasChanges || justCompleted) {
        setTimeout(throttleBump, justCompleted ? 500 : 0);
      }
    },
    [throttleBump],
  );

  useJobPolling(3000, handleJobsUpdated, ["started", "finished", "error"]);

  const handleNewDataset = () => setOpen(true);

  const handleDatasetCreated = useCallback(() => {
    bumpTable();
    checkQueueAndMaybeStartPolling();
  }, [bumpTable]);

  return (
    <>
      <CustomLayout title="Dataset Module" subtitle="Upload your datasets">
        <DatasetsTable
          handleNewDataset={handleNewDataset}
          updateTableFlag={updateTableFlag}
          setUpdateTableFlag={setUpdateTableFlag}
        />
        <DatasetModal
          open={open}
          setOpen={setOpen}
          updateDatasets={handleDatasetCreated}
        />
      </CustomLayout>

      <JobQueueWidget />
    </>
  );
}

export default DatasetsPage;
