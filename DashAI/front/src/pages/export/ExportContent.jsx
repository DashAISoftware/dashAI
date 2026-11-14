import { useEffect, useState } from "react";
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
import { getComponents } from "../../api/component";
import { getExportableDatasets } from "../../api/datasetExport";

/**
 * Dataset export flow (/app/data/export and /app/data/export/:exporterName).
 *
 * Mirrors the data hub: the Data module sidebar on the left, the current step
 * in the center and the chosen platform's details on the right. The URL holds
 * the step: no exporter means picking the platform, an exporter means picking
 * the dataset. Like the hub, it has no card in the Data module yet and is
 * reached by URL.
 */
export default function ExportContent() {
  const navigate = useNavigate();
  const { exporterName } = useParams();
  const threePanelLayout = useThreePanelLayout({ storageKey: "datasets" });

  const [exporters, setExporters] = useState([]);
  const [pendingExporter, setPendingExporter] = useState(null);

  const [datasets, setDatasets] = useState([]);
  const [datasetsLoading, setDatasetsLoading] = useState(false);
  const [datasetsError, setDatasetsError] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState(null);

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

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <DatasetsNotebooksLeftBar
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>

        <CenterPanel>
          {exporterName ? (
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
          ) : (
            <ExportPlatformStep
              exporters={exporters}
              selected={pendingExporter}
              onSelect={setPendingExporter}
              onBack={() => navigate("/app/data")}
              onNext={(exporter) =>
                navigate(`/app/data/export/${exporter.name}`)
              }
            />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          <ComponentDetailsPanel
            component={exporterName ? chosenExporter : pendingExporter}
          />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
