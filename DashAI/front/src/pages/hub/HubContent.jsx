import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import HubIcon from "@mui/icons-material/Hub";
import ScienceIcon from "@mui/icons-material/Science";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import SelectOptionMenu from "../../components/threeSectionLayout/SelectOptionMenu";
import HubLeftBar from "../../components/hub/HubLeftBar";
import DatasetGrid from "../../components/hub/DatasetGrid";
import DatasetDetail from "../../components/hub/DatasetDetail";
import HubImportPanel from "../../components/hub/HubImportPanel";
import ComponentDetailsPanel from "../../components/custom/ComponentDetailsPanel";
import DataloaderConfigBar from "../../components/notebooks/datasetCreation/DataloaderConfigBar";
import {
  deleteHubDownload,
  getDatasetSources,
  getHubDownload,
  listHubDownloads,
} from "../../api/hub";
import { enqueueHubDownloadJob } from "../../api/job";
import { useTranslation } from "react-i18next";

const POLL_INTERVAL_MS = 3000;

const SOURCE_ICONS = {
  HuggingFaceDatasetSource: HubIcon,
  OpenMLDatasetSource: ScienceIcon,
};

export default function HubContent() {
  const { t } = useTranslation(["hub"]);
  const navigate = useNavigate();
  const { sourceName: sourceNameParam } = useParams();
  const threePanelLayout = useThreePanelLayout({ storageKey: "hub" });

  const [sources, setSources] = useState([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [importMode, setImportMode] = useState(false);
  const [importStep, setImportStep] = useState(0);
  const [selectedDataloader, setSelectedDataloader] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [formHasErrors, setFormHasErrors] = useState(false);
  const formSubmitRef = useRef(null);

  const [downloads, setDownloads] = useState({});
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [importDownload, setImportDownload] = useState(null);

  const pollTimerRef = useRef(null);

  // Derive selected source from URL param + loaded sources list
  const selectedSource = sources.find((s) => s.name === sourceNameParam) ?? null;
  const sourceDisplayName =
    selectedSource?.display_name || selectedSource?.name || sourceNameParam;

  useEffect(() => {
    getDatasetSources()
      .then(setSources)
      .catch(() => setSources([]))
      .finally(() => setSourcesLoading(false));
  }, []);

  // Reset dataset selection when source changes
  useEffect(() => {
    setSelectedDataset(null);
    setImportMode(false);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
    setImportDownload(null);
  }, [sourceNameParam]);

  useEffect(() => {
    listHubDownloads()
      .then((rows) => {
        const map = {};
        for (const r of rows) map[`${r.source_name}::${r.dataset_id}`] = r;
        setDownloads(map);
      })
      .catch(() => {});
  }, []);

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
      if (!ds || !sourceNameParam) return null;
      return downloads[`${sourceNameParam}::${ds.id}`] ?? null;
    },
    [downloads, sourceNameParam],
  );

  const handleStartDownload = async () => {
    if (!selectedDataset || !sourceNameParam) return;
    setDownloadLoading(true);
    try {
      const row = await enqueueHubDownloadJob(
        sourceNameParam,
        selectedDataset.id,
        selectedDataset.name,
      );
      setDownloads((prev) => ({
        ...prev,
        [`${sourceNameParam}::${selectedDataset.id}`]: row,
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
    navigate(`/app/hub/${source.name}`);
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

  const sourceOptions = sources.map((source) => ({
    name: source.name,
    display_name: source.display_name || source.name,
    description: source.description || "",
    Icon: SOURCE_ICONS[source.name] ?? CloudDownloadIcon,
  }));

  const importSourceName = importDownload
    ? importDownload.source_name
    : sourceNameParam;

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <HubLeftBar
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
                  ? { id: importDownload.dataset_id, name: importDownload.name }
                  : selectedDataset
              }
              sourceName={importSourceName}
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
          ) : sourceNameParam ? (
            <DatasetGrid
              sourceName={sourceNameParam}
              sourceDisplayName={sourceDisplayName}
              selectedDataset={selectedDataset}
              onSelectDataset={setSelectedDataset}
            />
          ) : (
            <SelectOptionMenu
              title={t("hub:title")}
              subtitle={t("hub:selectSourceSubtitle")}
              options={sourceOptions}
              loading={sourcesLoading}
              searchBar
              goToNextStep={(name) =>
                handleSelectSource(sources.find((s) => s.name === name))
              }
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
              sourceName={sourceNameParam}
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
