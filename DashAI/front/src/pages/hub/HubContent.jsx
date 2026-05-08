import { useCallback, useEffect, useRef, useState } from "react";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import HubLeftBar from "../../components/hub/HubLeftBar";
import DatasetGrid from "../../components/hub/DatasetGrid";
import DatasetDetail from "../../components/hub/DatasetDetail";
import HubImportPanel from "../../components/hub/HubImportPanel";
import ComponentDetailsPanel from "../../components/custom/ComponentDetailsPanel";
import DataloaderConfigBar from "../../components/notebooks/datasetCreation/DataloaderConfigBar";
import {
  deleteHubDownload,
  getHubDownload,
  listHubDownloads,
} from "../../api/hub";
import { enqueueHubDownloadJob } from "../../api/job";

const POLL_INTERVAL_MS = 3000;

export default function HubContent() {
  const threePanelLayout = useThreePanelLayout({ storageKey: "hub" });
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [importMode, setImportMode] = useState(false);
  const [importStep, setImportStep] = useState(0);
  const [selectedDataloader, setSelectedDataloader] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [formHasErrors, setFormHasErrors] = useState(false);
  const formSubmitRef = useRef(null);

  // downloads: map of dataset_id -> HubDownload record
  const [downloads, setDownloads] = useState({});
  const [downloadLoading, setDownloadLoading] = useState(false);
  // download used in the current import flow (from left-bar "Add" button)
  const [importDownload, setImportDownload] = useState(null);

  const pollTimerRef = useRef(null);

  const sourceName = selectedSource?.name ?? null;

  // Load all existing downloads on mount
  useEffect(() => {
    listHubDownloads()
      .then((rows) => {
        const map = {};
        for (const r of rows) map[`${r.source_name}::${r.dataset_id}`] = r;
        setDownloads(map);
      })
      .catch(() => {});
  }, []);

  // Poll in-progress downloads
  useEffect(() => {
    const inProgress = Object.values(downloads).filter(
      (d) => d.status === "downloading",
    );
    if (inProgress.length === 0) {
      clearInterval(pollTimerRef.current);
      return;
    }

    pollTimerRef.current = setInterval(async () => {
      const updates = await Promise.allSettled(
        inProgress.map((d) => getHubDownload(d.id)),
      );
      setDownloads((prev) => {
        const next = { ...prev };
        for (const res of updates) {
          if (res.status === "fulfilled") {
            const r = res.value;
            next[`${r.source_name}::${r.dataset_id}`] = r;
          }
        }
        return next;
      });
    }, POLL_INTERVAL_MS);

    return () => clearInterval(pollTimerRef.current);
  }, [downloads]);

  const getDownloadForDataset = useCallback(
    (ds) => {
      if (!ds || !sourceName) return null;
      return downloads[`${sourceName}::${ds.id}`] ?? null;
    },
    [downloads, sourceName],
  );

  const handleStartDownload = async () => {
    if (!selectedDataset || !sourceName) return;
    setDownloadLoading(true);
    try {
      const row = await enqueueHubDownloadJob(
        sourceName,
        selectedDataset.id,
        selectedDataset.name,
      );
      setDownloads((prev) => ({
        ...prev,
        [`${sourceName}::${selectedDataset.id}`]: row,
      }));
    } catch {
      // error shown via download status
    } finally {
      setDownloadLoading(false);
    }
  };

  const handleDeleteDownload = async (downloadId) => {
    try {
      await deleteHubDownload(downloadId);
      setDownloads((prev) => {
        const next = { ...prev };
        for (const key of Object.keys(next)) {
          if (next[key].id === downloadId) delete next[key];
        }
        return next;
      });
    } catch {
      // ignore
    }
  };

  const handleImportDownload = (dl) => {
    setImportDownload(dl);
    setImportMode(true);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
  };

  const handleSelectSource = (source) => {
    setSelectedSource(source);
    setSelectedDataset(null);
    setImportMode(false);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
    setImportDownload(null);
  };

  const handleImported = () => {
    setSelectedDataset(null);
    setImportMode(false);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
    setImportDownload(null);
  };

  const handleStartImport = () => {
    setImportDownload(getDownloadForDataset(selectedDataset));
    setImportMode(true);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
  };

  const handleExitImport = () => {
    setImportMode(false);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
    setImportDownload(null);
  };

  const downloadsList = Object.values(downloads);

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <HubLeftBar
            selectedSource={sourceName}
            onSelectSource={handleSelectSource}
            downloads={downloadsList}
            onDeleteDownload={handleDeleteDownload}
            onImportDownload={handleImportDownload}
          />
        </LeftPanel>

        <CenterPanel>
          {importMode ? (
            <HubImportPanel
              dataset={
                importDownload
                  ? {
                      id: importDownload.dataset_id,
                      name: importDownload.name,
                    }
                  : selectedDataset
              }
              sourceName={
                importDownload ? importDownload.source_name : sourceName
              }
              hubDownload={importDownload}
              step={importStep}
              onStepChange={setImportStep}
              selectedLoader={selectedDataloader}
              onSelectedLoaderChange={setSelectedDataloader}
              formValues={formValues}
              formHasErrors={formHasErrors}
              onCancel={handleExitImport}
              onImported={handleImported}
            />
          ) : (
            <DatasetGrid
              sourceName={sourceName}
              selectedDataset={selectedDataset}
              onSelectDataset={setSelectedDataset}
            />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          {importMode ? (
            importStep === 0 ? (
              <ComponentDetailsPanel component={selectedDataloader} />
            ) : (
              <DataloaderConfigBar
                selectedDataloader={selectedDataloader?.name}
                formSubmitRef={formSubmitRef}
                setError={setFormHasErrors}
                onValuesChange={setFormValues}
              />
            )
          ) : (
            <DatasetDetail
              dataset={selectedDataset}
              sourceName={sourceName}
              download={getDownloadForDataset(selectedDataset)}
              downloadLoading={downloadLoading}
              onStartDownload={handleStartDownload}
              onStartImport={handleStartImport}
            />
          )}
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
