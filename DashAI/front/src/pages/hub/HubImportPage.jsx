import { useCallback, useEffect, useRef, useState } from "react";
import { useMatch, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Box, CircularProgress, Typography } from "@mui/material";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import DatasetsNotebooksLeftBar from "../../components/notebooks/DatasetNotebookLeftBar";
import HubImportPanel from "../../components/hub/HubImportPanel";
import DatafileInfoPanel from "../../components/hub/DatafileInfoPanel";
import ComponentDetailsPanel from "../../components/custom/ComponentDetailsPanel";
import DataloaderConfigBar from "../../components/notebooks/datasetCreation/DataloaderConfigBar";
import { getComponents } from "../../api/component";
import { getDatafile } from "../../api/hub";
import { useDatasetsAndNotebooks } from "../../components/custom/contexts/DatasetsAndNotebooksContext";

export default function HubImportPage() {
  const { datafileId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation(["hub", "common"]);
  const threePanelLayout = useThreePanelLayout({ storageKey: "datasets" });
  const { addDatasetOptimistically, startDatasetPolling } =
    useDatasetsAndNotebooks();

  const previewMatch = useMatch(
    "/app/data/hub/import/:datafileId/loader/:loaderName/preview",
  );
  const loaderWithNameMatch = useMatch(
    "/app/data/hub/import/:datafileId/loader/:loaderName",
  );
  const loaderMatch = useMatch("/app/data/hub/import/:datafileId/loader");

  const loaderName =
    previewMatch?.params.loaderName ??
    loaderWithNameMatch?.params.loaderName ??
    null;

  const dataloaderStep = 1;
  const previewStep = 2;
  const step = previewMatch
    ? previewStep
    : loaderWithNameMatch || loaderMatch
      ? dataloaderStep
      : 0;

  const [datafile, setDatafile] = useState(null);
  const [datafileLoading, setDatafileLoading] = useState(true);
  const [dataloaders, setDataloaders] = useState([]);
  const [formValues, setFormValues] = useState({});
  const [formHasErrors, setFormHasErrors] = useState(false);
  const formSubmitRef = useRef(null);

  useEffect(() => {
    if (!datafileId) return;
    setDatafileLoading(true);
    getDatafile(parseInt(datafileId))
      .then(setDatafile)
      .catch(() => navigate("/app/data/hub"))
      .finally(() => setDatafileLoading(false));
  }, [datafileId, navigate]);

  useEffect(() => {
    getComponents({ selectTypes: ["DataLoader"] })
      .then(setDataloaders)
      .catch(() => setDataloaders([]));
  }, []);

  // Reset form when selected loader changes
  useEffect(() => {
    setFormValues({});
    setFormHasErrors(false);
  }, [loaderName]);

  const selectedLoader = loaderName
    ? (dataloaders.find((d) => d.name === loaderName) ?? null)
    : null;

  const dataset = datafile
    ? { id: datafile.dataset_id, name: datafile.name }
    : null;

  const sourceName = datafile?.source_name ?? null;

  const base = `/app/data/hub/import/${datafileId}`;

  const handleStepChange = useCallback(
    (newStepOrFn) => {
      const newStep =
        typeof newStepOrFn === "function" ? newStepOrFn(step) : newStepOrFn;
      if (newStep === 0) navigate(base);
      else if (newStep === 1)
        navigate(
          loaderName ? `${base}/loader/${loaderName}` : `${base}/loader`,
        );
      else if (newStep === 2) navigate(`${base}/loader/${loaderName}/preview`);
    },
    [step, base, loaderName, navigate],
  );

  const handleLoaderChange = useCallback(
    (loader) => {
      navigate(loader ? `${base}/loader/${loader.name}` : `${base}/loader`, {
        replace: true,
      });
    },
    [base, navigate],
  );

  const handleCancel = () =>
    navigate(sourceName ? `/app/data/hub/${sourceName}` : "/app/data/hub");
  const handleImported = (dataset, importResult) => {
    addDatasetOptimistically(dataset);
    if (importResult?.job_id) {
      startDatasetPolling(dataset, { id: importResult.job_id });
    }
    navigate(`/app/data/datasets/${dataset.id}`);
  };

  const handleDownloadDelete = (id) => {
    if (id === parseInt(datafileId)) {
      navigate(sourceName ? `/app/data/hub/${sourceName}` : "/app/data/hub");
    }
  };

  const renderRightPanel = () => {
    if (step < dataloaderStep) return <DatafileInfoPanel datafile={datafile} />;
    if (step === dataloaderStep)
      return <ComponentDetailsPanel component={selectedLoader} />;
    return (
      <DataloaderConfigBar
        selectedDataloader={loaderName}
        formSubmitRef={formSubmitRef}
        setError={setFormHasErrors}
        onValuesChange={setFormValues}
      />
    );
  };

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <DatasetsNotebooksLeftBar
            onToggle={threePanelLayout.handleToggleLeft}
            onDownloadDelete={handleDownloadDelete}
          />
        </LeftPanel>

        <CenterPanel>
          {datafileLoading ? (
            <Box
              sx={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                height: "100%",
                gap: 2,
              }}
            >
              <CircularProgress color="primary" />
              <Typography>{t("common:loading")}</Typography>
            </Box>
          ) : (
            <HubImportPanel
              dataset={dataset}
              sourceName={sourceName}
              datafile={datafile}
              step={step}
              onStepChange={handleStepChange}
              selectedLoader={selectedLoader}
              onSelectedLoaderChange={handleLoaderChange}
              formValues={formValues}
              formHasErrors={formHasErrors}
              onCancel={handleCancel}
              onImported={handleImported}
            />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">{renderRightPanel()}</RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
