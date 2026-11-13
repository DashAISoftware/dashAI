import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import ComponentDetailsPanel from "../../components/custom/ComponentDetailsPanel";
import DatasetsNotebooksLeftBar from "../../components/notebooks/DatasetNotebookLeftBar";
import ExportPlatformStep from "../../components/export/ExportPlatformStep";
import { getComponents } from "../../api/component";

/**
 * Entry page of the dataset export flow (/app/data/export).
 *
 * Mirrors the data hub: the Data module sidebar on the left, the platform
 * picker in the center and the selected platform's details on the right. Like
 * the hub, it has no card in the Data module yet and is reached by URL.
 */
export default function ExportContent() {
  const navigate = useNavigate();
  const threePanelLayout = useThreePanelLayout({ storageKey: "datasets" });

  const [exporters, setExporters] = useState([]);
  const [selectedExporter, setSelectedExporter] = useState(null);

  useEffect(() => {
    getComponents({ selectTypes: "DatasetExporter" })
      .then(setExporters)
      .catch(() => setExporters([]));
  }, []);

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <DatasetsNotebooksLeftBar
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>

        <CenterPanel>
          <ExportPlatformStep
            exporters={exporters}
            selected={selectedExporter}
            onSelect={setSelectedExporter}
            onBack={() => navigate("/app/data")}
            onNext={(exporter) => navigate(`/app/data/export/${exporter.name}`)}
          />
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          <ComponentDetailsPanel component={selectedExporter} />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
