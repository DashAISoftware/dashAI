import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Box, Typography } from "@mui/material";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import HubBreadcrumbs from "../../components/hub/HubBreadcrumbs";
import ComponentSelector from "../../components/custom/ComponentSelector";
import ComponentDetailsPanel from "../../components/custom/ComponentDetailsPanel";
import StepperNavigationFooter from "../../components/shared/StepperNavigationFooter";
import DatasetsNotebooksLeftBar from "../../components/notebooks/DatasetNotebookLeftBar";
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
import { useDatasetsAndNotebooks } from "../../components/custom/contexts/DatasetsAndNotebooksContext";

export default function HubContent() {
  const { t } = useTranslation(["hub"]);
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const { addDownload, updateDownload } = useDatasetsAndNotebooks();
  const { sourceName: sourceNameParam } = useParams();
  const threePanelLayout = useThreePanelLayout({ storageKey: "datasets" });

  const [sources, setSources] = useState([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [selectedDataset, setSelectedDataset] = useState(null);

  const [pendingSource, setPendingSource] = useState(null);

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
          updateDownload(updated);
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
      const entry = { ...row, job_id: job.id };
      setDownloads((prev) => ({
        ...prev,
        [`${sourceNameParam}::${selectedDataset.id}`]: entry,
      }));
      addDownload(entry);
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

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <DatasetsNotebooksLeftBar
            onToggle={threePanelLayout.handleToggleLeft}
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
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                width: "100%",
                height: "100%",
                px: 2,
                pt: 2,
              }}
            >
              <HubBreadcrumbs />
              <Box sx={{ mb: 2 }}>
                <Typography variant="h5" component="h1">
                  {t("hub:selectSourceTitle")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("hub:selectSourceSubtitle")}
                </Typography>
              </Box>
              <Box sx={{ flex: 1, minHeight: 0, pb: 4 }}>
                <ComponentSelector
                  components={sources.map((s) => ({
                    ...s,
                    category: s.metadata?.category,
                  }))}
                  selected={pendingSource}
                  onSelect={setPendingSource}
                  searchPlaceholder={t("hub:searchSources")}
                />
              </Box>
              <StepperNavigationFooter
                onBack={() => navigate("/app/data")}
                onNext={() => handleSelectSource(pendingSource)}
                nextDisabled={!pendingSource}
              />
            </Box>
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          {!sourceNameParam ? (
            <ComponentDetailsPanel component={pendingSource} />
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
