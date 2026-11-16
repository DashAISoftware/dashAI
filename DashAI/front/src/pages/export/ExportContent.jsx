import { useEffect, useMemo, useRef, useState } from "react";
import {
  useLocation,
  useMatch,
  useNavigate,
  useParams,
} from "react-router-dom";
import { useTranslation } from "react-i18next";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import ComponentDetailsPanel from "../../components/custom/ComponentDetailsPanel";
import DatasetsNotebooksLeftBar from "../../components/notebooks/DatasetNotebookLeftBar";
import ExportPlatformStep from "../../components/export/ExportPlatformStep";
import ExportDatasetStep from "../../components/export/ExportDatasetStep";
import ExportMetadataStep from "../../components/export/ExportMetadataStep";
import ExportMetadataPanel from "../../components/export/ExportMetadataPanel";
import ExportReviewStep from "../../components/export/ExportReviewStep";
import ExportProgressStep from "../../components/export/ExportProgressStep";
import ExportHistoryPanel from "../../components/export/ExportHistoryPanel";
import { getComponents } from "../../api/component";
import {
  createExport,
  getExport,
  getExportableDatasets,
  listExports,
  validateExport,
} from "../../api/datasetExport";

/** How often a running export is checked, in milliseconds. */
const STATUS_POLL_MS = 2000;
const FINISHED_STATUSES = ["published", "error"];
import { getDatasetSample, getDatasetTypes } from "../../api/datasets";

/** Turn an API error into a readable message, or null to use a generic one. */
const errorDetail = (error) => {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) return detail.join("; ");
  return typeof detail === "string" ? detail : null;
};

/**
 * Dataset export flow (/app/data/export/[:exporterName[/:datasetId[/review]]]
 * and /app/data/export/status/:exportId).
 *
 * Mirrors the data hub: the Data module sidebar on the left, the current step
 * in the center and the platform's details or form on the right. The URL holds
 * the step: no exporter means picking the platform, an exporter means picking
 * the dataset, a dataset means filling in the export metadata, /review means
 * reviewing and publishing, and status/:exportId follows a publication. The
 * metadata travels between the metadata and review steps in the navigation
 * state. Like the hub, it has no card in the Data module yet and is reached
 * by URL.
 */
export default function ExportContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation(["export"]);
  const { exporterName, datasetId } = useParams();
  const isReview = Boolean(
    useMatch("/app/data/export/:exporterName/:datasetId/review"),
  );
  const exportId = useMatch("/app/data/export/status/:exportId")?.params
    .exportId;
  const stateParams = location.state?.params ?? null;
  const threePanelLayout = useThreePanelLayout({ storageKey: "datasets" });

  const [exporters, setExporters] = useState([]);
  const [pendingExporter, setPendingExporter] = useState(null);

  const [datasets, setDatasets] = useState([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [datasetsError, setDatasetsError] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState(null);

  const [columns, setColumns] = useState([]);
  const [sample, setSample] = useState(null);
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [datasetError, setDatasetError] = useState(false);
  const [target, setTarget] = useState("");
  const [ignored, setIgnored] = useState([]);
  const [formValues, setFormValues] = useState({});
  const [formHasErrors, setFormHasErrors] = useState(false);
  const formSubmitRef = useRef(null);

  const [validation, setValidation] = useState({
    loading: false,
    errors: [],
    warnings: [],
    failed: false,
  });
  const [confirmed, setConfirmed] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [publishError, setPublishError] = useState(null);

  const [exportRow, setExportRow] = useState(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportNotFound, setExportNotFound] = useState(false);
  const [history, setHistory] = useState([]);

  const chosenExporter = exporters.find((e) => e.name === exporterName) ?? null;
  const platformName =
    chosenExporter?.display_name || chosenExporter?.name || exporterName;
  const fieldTitles = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(chosenExporter?.schema?.properties ?? {}).map(
          ([key, property]) => [key, property.title ?? key],
        ),
      ),
    [chosenExporter],
  );

  useEffect(() => {
    getComponents({ selectTypes: "DatasetExporter" })
      .then(setExporters)
      .catch(() => setExporters([]));
  }, []);

  useEffect(() => {
    setSelectedDataset(null);
    if (!exporterName) return;
    setDatasetsLoading(true);
    setDatasetsError(false);
    getExportableDatasets(exporterName)
      .then(setDatasets)
      .catch(() => {
        setDatasets([]);
        setDatasetsError(true);
      })
      .finally(() => setDatasetsLoading(false));
  }, [exporterName]);

  const exportDataset =
    datasets.find((d) => String(d.id) === String(datasetId)) ?? null;
  const datasetName = exportDataset?.name ?? "";
  const unsupportedColumns =
    exportDataset?.compatibility.unsupported_columns ?? [];
  const storableColumns = columns.filter(
    (column) => !unsupportedColumns.includes(column),
  );
  // The schema form reinitializes when this object changes, so it is built
  // once per dataset (or per return from the review) rather than per render.
  const initialFormValues = useMemo(() => {
    if (stateParams) return stateParams;
    return datasetName ? { name: datasetName } : {};
  }, [stateParams, datasetName]);

  useEffect(() => {
    // Coming back from the review restores what the user had chosen.
    setTarget(stateParams?.default_target_attribute ?? "");
    setIgnored(stateParams?.ignore_attribute ?? []);
    setFormValues(stateParams ?? {});
    if (!datasetId) return;
    setDatasetLoading(true);
    setDatasetError(false);
    Promise.all([getDatasetTypes(datasetId), getDatasetSample(datasetId)])
      .then(([types, rows]) => {
        setColumns(Object.keys(types ?? {}));
        setSample(rows);
      })
      .catch(() => {
        setColumns([]);
        setSample(null);
        setDatasetError(true);
      })
      .finally(() => setDatasetLoading(false));
  }, [datasetId]);

  useEffect(() => {
    setConfirmed(false);
    setPublishError(null);
    if (!isReview || !stateParams) return;
    let cancelled = false;
    setValidation({ loading: true, errors: [], warnings: [], failed: false });
    validateExport(exporterName, Number(datasetId), stateParams)
      .then(({ errors, warnings }) => {
        if (!cancelled) {
          setValidation({
            loading: false,
            errors: errors ?? [],
            warnings: warnings ?? [],
            failed: false,
          });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setValidation({
            loading: false,
            errors: [],
            warnings: [],
            failed: true,
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isReview, stateParams, exporterName, datasetId]);

  // Follow an export: read it now and every few seconds while its job runs.
  useEffect(() => {
    setExportRow(null);
    setExportNotFound(false);
    if (!exportId) return undefined;
    let cancelled = false;
    let timer = null;

    const poll = () => {
      getExport(Number(exportId))
        .then((row) => {
          if (cancelled) return;
          setExportRow(row);
          if (FINISHED_STATUSES.includes(row.status)) {
            if (row.dataset_id) {
              listExports(row.dataset_id)
                .then((rows) => !cancelled && setHistory(rows))
                .catch(() => {});
            }
          } else {
            timer = setTimeout(poll, STATUS_POLL_MS);
          }
        })
        .catch(() => {
          if (!cancelled) setExportNotFound(true);
        })
        .finally(() => !cancelled && setExportLoading(false));
    };

    setExportLoading(true);
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [exportId]);

  useEffect(() => {
    if (!exportRow?.dataset_id) return;
    listExports(exportRow.dataset_id)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [exportRow?.dataset_id]);

  const platformLabel = (name) => {
    const exporter = exporters.find((e) => e.name === name);
    return exporter?.display_name || name;
  };

  const metadataUrl = `/app/data/export/${exporterName}/${datasetId}`;

  const handleReview = () => {
    const params = {
      ...formValues,
      default_target_attribute: target,
      ignore_attribute: ignored.length ? ignored : null,
    };
    navigate(`${metadataUrl}/review`, { state: { params } });
  };

  const handlePublish = async () => {
    setPublishing(true);
    setPublishError(null);
    try {
      const created = await createExport(
        exporterName,
        Number(datasetId),
        stateParams,
      );
      navigate(`/app/data/export/status/${created.export_id}`);
    } catch (error) {
      setPublishError(errorDetail(error) ?? t("export:publishFailed"));
    } finally {
      setPublishing(false);
    }
  };

  const renderCenter = () => {
    if (exportId) {
      const rowExporter = exportRow?.exporter_name;
      return (
        <ExportProgressStep
          exportRow={exportRow}
          platformName={platformLabel(rowExporter ?? "")}
          loading={exportLoading}
          notFound={exportNotFound}
          onPlatformClick={() =>
            navigate(
              rowExporter
                ? `/app/data/export/${rowExporter}`
                : "/app/data/export",
            )
          }
          onDatasetClick={() =>
            navigate(`/app/data/datasets/${exportRow.dataset_id}`)
          }
          onRetry={() =>
            navigate(
              `/app/data/export/${rowExporter}/${exportRow.dataset_id}/review`,
              { state: { params: exportRow.params } },
            )
          }
        />
      );
    }
    if (isReview) {
      const totalColumns = columns.length || exportDataset?.total_columns || 0;
      return (
        <ExportReviewStep
          platformName={platformName}
          datasetName={datasetName || String(datasetId)}
          params={stateParams}
          fieldTitles={fieldTitles}
          summary={{
            rows: exportDataset?.total_rows ?? null,
            columns: totalColumns,
            sentColumns: totalColumns - unsupportedColumns.length,
            leftOut: unsupportedColumns,
          }}
          validation={validation}
          confirmed={confirmed}
          onConfirmChange={setConfirmed}
          publishing={publishing}
          publishError={publishError}
          onPlatformClick={() => navigate(`/app/data/export/${exporterName}`)}
          onBack={() =>
            navigate(metadataUrl, {
              state: stateParams ? { params: stateParams } : undefined,
            })
          }
          onPublish={handlePublish}
        />
      );
    }
    if (datasetId) {
      return (
        <ExportMetadataStep
          platformName={platformName}
          datasetName={datasetName || String(datasetId)}
          columns={columns}
          sample={sample}
          unsupportedColumns={unsupportedColumns}
          target={target}
          ignored={ignored}
          loading={datasetLoading || datasetsLoading}
          error={datasetError}
          canContinue={Boolean(target) && !formHasErrors}
          onPlatformClick={() => navigate(`/app/data/export/${exporterName}`)}
          onBack={() => navigate(`/app/data/export/${exporterName}`)}
          onNext={handleReview}
        />
      );
    }
    if (exporterName) {
      return (
        <ExportDatasetStep
          platformName={platformName}
          datasets={datasets}
          loading={datasetsLoading}
          error={datasetsError}
          selected={selectedDataset}
          onSelect={setSelectedDataset}
          onBack={() => navigate("/app/data/export")}
          onNext={(dataset) =>
            navigate(`/app/data/export/${exporterName}/${dataset.id}`)
          }
        />
      );
    }
    return (
      <ExportPlatformStep
        exporters={exporters}
        selected={pendingExporter}
        onSelect={setPendingExporter}
        onBack={() => navigate("/app/data")}
        onNext={(exporter) => navigate(`/app/data/export/${exporter.name}`)}
      />
    );
  };

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <DatasetsNotebooksLeftBar
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>

        <CenterPanel>{renderCenter()}</CenterPanel>

        <RightPanel toggleButtonTop="50%">
          {exportId ? (
            <ExportHistoryPanel
              datasetName={exportRow?.dataset_name ?? ""}
              exports={history}
              currentId={exportRow?.id}
              platformLabel={platformLabel}
              onSelect={(row) => navigate(`/app/data/export/status/${row.id}`)}
            />
          ) : datasetId && !isReview ? (
            <ExportMetadataPanel
              exporterName={exporterName}
              columns={storableColumns}
              target={target}
              ignored={ignored}
              onTargetChange={setTarget}
              onIgnoredChange={setIgnored}
              initialValues={initialFormValues}
              formSubmitRef={formSubmitRef}
              onValuesChange={setFormValues}
              setError={setFormHasErrors}
            />
          ) : (
            <ComponentDetailsPanel
              component={exporterName ? chosenExporter : pendingExporter}
            />
          )}
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
