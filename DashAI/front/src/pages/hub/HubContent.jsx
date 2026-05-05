import { useState } from "react";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import HubLeftBar from "../../components/hub/HubLeftBar";
import DatasetGrid from "../../components/hub/DatasetGrid";
import DatasetDetail from "../../components/hub/DatasetDetail";

export default function HubContent() {
  const threePanelLayout = useThreePanelLayout({ storageKey: "hub" });
  const [selectedSource, setSelectedSource] = useState(null);
  const [selectedDataset, setSelectedDataset] = useState(null);

  const handleSelectSource = (sourceName) => {
    setSelectedSource(sourceName);
    setSelectedDataset(null);
  };

  const handleImported = () => {
    setSelectedDataset(null);
  };

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <HubLeftBar
            selectedSource={selectedSource}
            onSelectSource={handleSelectSource}
          />
        </LeftPanel>

        <CenterPanel>
          <DatasetGrid
            sourceName={selectedSource}
            selectedDataset={selectedDataset}
            onSelectDataset={setSelectedDataset}
          />
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          <DatasetDetail
            dataset={selectedDataset}
            sourceName={selectedSource}
            onImported={handleImported}
          />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
