import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
import { getComponents } from "../../api/component";
import { getExportableDatasets } from "../../api/datasetExport";
import { getDatasetSample, getDatasetTypes } from "../../api/datasets";

/**
 * Dataset export flow (/app/data/export/[:exporterName[/:datasetId]]).
 *
 * Mirrors the data hub: the Data module sidebar on the left, the current step
 * in the center and the platform's details or form on the right. The URL holds
 * the step: no exporter means picking the platform, an exporter means picking
 * the dataset, and a dataset means filling in the export metadata. Like the
 * hub, it has no card in the Data module yet and is reached by URL.
 */
export default function ExportContent() {
  const navigate = useNavigate();
  const { exporterName, datasetId } = useParams();
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

  const chosenExporter = exporters.find((e) => e.name === exporterName) ?? null;
  const platformName =
    chosenExporter?.display_name || chosenExporter?.name || exporterName;

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
  // once per dataset rather than on every render.
  const initialFormValues = useMemo(
    () => (datasetName ? { name: datasetName } : {}),
    [datasetName],
  );

  useEffect(() => {
    setTarget("");
    setIgnored([]);
    setFormValues({});
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

  const handleReview = () => {
    const params = {
      ...formValues,
      default_target_attribute: target,
      ignore_attribute: ignored.length ? ignored : null,
    };
    navigate(`/app/data/export/${exporterName}/${datasetId}/review`, {
      state: { params },
    });
  };

  const renderCenter = () => {
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
          {datasetId ? (
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
