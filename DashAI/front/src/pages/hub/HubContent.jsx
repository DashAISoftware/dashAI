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
import {
  createDatafile,
  deleteDatafile,
  getDatafile,
  listDatafiles,
} from "../../api/hub";

import { getComponents } from "../../api/component";
import { enqueueDatafileJob } from "../../api/job";
import { startJobPolling } from "../../hooks/useJobPolling";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";

const SOURCE_ICONS = {
  HuggingFaceDatasetSource: HubIcon,
  OpenMLDatasetSource: ScienceIcon,
};

export default function HubContent() {
  const { t } = useTranslation(["hub"]);
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const { sourceName: sourceNameParam } = useParams();
  const threePanelLayout = useThreePanelLayout({ storageKey: "hub" });

  const [sources, setSources] = useState([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [selectedDataset, setSelectedDataset] = useState(null);

  const [downloads, setDownloads] = useState({});
  const [downloadLoading, setDownloadLoading] = useState(false);

  const watchedJobsRef = useRef(new Set());

  // Derive selected source from URL param + loaded sources list
  const selectedSource =
    sources.find((s) => s.name === sourceNameParam) ?? null;
  const sourceDisplayName =
    selectedSource?.display_name || selectedSource?.name || sourceNameParam;

  useEffect(() => {
    getComponents({ selectTypes: "DatasetSource" })
      .then(setSources)
      .catch(() => setSources([]))
      .finally(() => setSourcesLoading(false));
  }, [t]);

  // Reset dataset selection when source changes
  useEffect(() => {
    setSelectedDataset(null);
  }, [sourceNameParam]);

  useEffect(() => {
    listDatafiles()
      .then((rows) => {
        const map = {};
        for (const r of rows) map[`${r.source_name}::${r.dataset_id}`] = r;
        setDownloads(map);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const downloading = Object.values(downloads).filter(
      (d) => d.status === "downloading" && d.job_id,
    );

    for (const d of downloading) {
      if (watchedJobsRef.current.has(d.job_id)) continue;
      watchedJobsRef.current.add(d.job_id);

      const onDone = async (isError) => {
        try {
          const updated = await getDatafile(d.id);
          setDownloads((prev) => ({
            ...prev,
            [`${updated.source_name}::${updated.dataset_id}`]: updated,
          }));
          if (isError) {
            enqueueSnackbar(
              `${t("hub:downloadFailed")}: ${d.name} - ${t("hub:checkQueue")}`,
              { variant: "error" },
            );
          } else {
            enqueueSnackbar(t("hub:downloaded") + `: ${d.name}`, {
              variant: "success",
            });
          }
        } catch {
          // ignore
        } finally {
          watchedJobsRef.current.delete(d.job_id);
        }
      };

      startJobPolling(
        d.job_id,
        () => onDone(false),
        () => onDone(true),
      );
    }
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
      const row = await createDatafile(
        sourceNameParam,
        selectedDataset.id,
        selectedDataset.name,
        selectedDataset.description ?? "",
        selectedDataset.tags ?? [],
        selectedDataset.url ?? "",
      );
      const job = await enqueueDatafileJob(
        row.id,
        sourceNameParam,
        selectedDataset.id,
      );
      setDownloads((prev) => ({
        ...prev,
        [`${sourceNameParam}::${selectedDataset.id}`]: {
          ...row,
          job_id: job.id,
        },
      }));
    } catch {
      // error shown via download status
    } finally {
      setDownloadLoading(false);
    }
  };

  const handleDeleteDownload = async (downloadId) => {
    const name =
      Object.values(downloads).find((d) => d.id === downloadId)?.name ?? "";
    try {
      await deleteDatafile(downloadId);
      setDownloads((prev) => {
        const next = { ...prev };
        for (const key of Object.keys(next)) {
          if (next[key].id === downloadId) delete next[key];
        }
        return next;
      });
      enqueueSnackbar(t("hub:deleteSuccess", { name }), { variant: "success" });
    } catch {
      enqueueSnackbar(t("hub:deleteError"), { variant: "error" });
    }
  };

  const handleImportDownload = (dl) => {
    navigate(`/app/data/hub/import/${dl.id}`);
  };

  const handleSelectSource = (source) => {
    navigate(`/app/data/hub/${source.name}`);
  };

  const handleStartImport = () => {
    const dl = getDownloadForDataset(selectedDataset);
    if (dl) navigate(`/app/data/hub/import/${dl.id}`);
  };

  const downloadsList = Object.values(downloads);

  const sourceOptions = sources.map((source) => ({
    name: source.name,
    display_name: source.display_name || source.name,
    description: source.description || "",
    Icon: SOURCE_ICONS[source.name] ?? CloudDownloadIcon,
  }));

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
          {sourceNameParam ? (
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
              goToNextStep={(name) =>
                handleSelectSource(sources.find((s) => s.name === name))
              }
            />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          <DatasetDetail
            dataset={selectedDataset}
            sourceName={sourceNameParam}
            download={getDownloadForDataset(selectedDataset)}
            downloadLoading={downloadLoading}
            onStartDownload={handleStartDownload}
            onStartImport={handleStartImport}
          />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
