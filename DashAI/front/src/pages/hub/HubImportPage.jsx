import { useCallback, useEffect, useRef, useState } from "react";
import { useMatch, useNavigate, useParams } from "react-router-dom";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import HubLeftBar from "../../components/hub/HubLeftBar";
import HubImportPanel from "../../components/hub/HubImportPanel";
import DatafileInfoPanel from "../../components/hub/DatafileInfoPanel";
import ComponentDetailsPanel from "../../components/custom/ComponentDetailsPanel";
import DataloaderConfigBar from "../../components/notebooks/datasetCreation/DataloaderConfigBar";
import { getComponents } from "../../api/component";
import { deleteDatafile, getDatafile, listDatafiles } from "../../api/hub";

export default function HubImportPage() {
  const { datafileId } = useParams();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["hub"]);
  const threePanelLayout = useThreePanelLayout({ storageKey: "hub" });

  const previewMatch = useMatch(
    "/app/hub/import/:datafileId/loader/:loaderName/preview",
  );
  const loaderWithNameMatch = useMatch(
    "/app/hub/import/:datafileId/loader/:loaderName",
  );
  const loaderMatch = useMatch("/app/hub/import/:datafileId/loader");

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
  const [dataloaders, setDataloaders] = useState([]);
  const [downloads, setDownloads] = useState([]);
  const [formValues, setFormValues] = useState({});
  const [formHasErrors, setFormHasErrors] = useState(false);
  const formSubmitRef = useRef(null);

  useEffect(() => {
    if (!datafileId) return;
    getDatafile(parseInt(datafileId))
      .then(setDatafile)
      .catch(() => navigate("/app/hub"));
  }, [datafileId, navigate]);

  useEffect(() => {
    getComponents({ selectTypes: ["DataLoader"] })
      .then(setDataloaders)
      .catch(() => setDataloaders([]));
  }, []);

  useEffect(() => {
    listDatafiles()
      .then(setDownloads)
      .catch(() => {});
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

  const base = `/app/hub/import/${datafileId}`;

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
    navigate(sourceName ? `/app/hub/${sourceName}` : "/app/hub");
  const handleImported = () =>
    navigate(sourceName ? `/app/hub/${sourceName}` : "/app/hub");

  const handleDeleteDownload = async (downloadId) => {
    try {
      await deleteDatafile(downloadId);
      setDownloads((prev) => prev.filter((d) => d.id !== downloadId));
      if (downloadId === parseInt(datafileId)) {
        navigate(sourceName ? `/app/hub/${sourceName}` : "/app/hub");
      }
    } catch {
      enqueueSnackbar(t("hub:deleteError"), { variant: "error" });
    }
  };

  const handleImportDownload = (dl) => {
    navigate(`/app/hub/import/${dl.id}`);
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
          <HubLeftBar
            downloads={downloads}
            onDeleteDownload={handleDeleteDownload}
            onImportDownload={handleImportDownload}
          />
        </LeftPanel>

        <CenterPanel>
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
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">{renderRightPanel()}</RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
