import { useRef, useState } from "react";
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

  const sourceName = selectedSource?.name ?? null;

  const handleSelectSource = (source) => {
    setSelectedSource(source);
    setSelectedDataset(null);
    setImportMode(false);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
  };

  const handleImported = () => {
    setSelectedDataset(null);
    setImportMode(false);
    setImportStep(0);
    setSelectedDataloader(null);
    setFormValues({});
    setFormHasErrors(false);
  };

  const handleStartImport = () => {
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
  };

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <HubLeftBar
            selectedSource={sourceName}
            onSelectSource={handleSelectSource}
          />
        </LeftPanel>

        <CenterPanel>
          {importMode ? (
            <HubImportPanel
              dataset={selectedDataset}
              sourceName={sourceName}
              compatibleComponents={selectedSource?.compatible_components ?? []}
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
              onStartImport={handleStartImport}
            />
          )}
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
