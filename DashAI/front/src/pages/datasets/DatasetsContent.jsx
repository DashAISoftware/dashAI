import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import DatasetsNotebooksLeftBar from "../../components/notebooks/DatasetNotebookLeftBar";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightBar from "../../components/notebooks/RightBar";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import DatasetsCenterContent from "../../components/notebooks/dataset/DatasetsCenterContent";
import { TourProvider } from "../../components/tour/TourProvider";
import { TOUR_KEYS } from "../../constants/tours";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useDatasetsAndNotebooks } from "../../components/custom/contexts/DatasetsAndNotebooksContext";
import { useTranslation } from "react-i18next";

export default function DatasetsContent() {
  const { t } = useTranslation();
  const threePanelLayout = useThreePanelLayout();

  const {
    notebooks,
    selectedNotebookId,
    selectedDatasetId,
    rightBarContent,
    step,
  } = useDatasetsAndNotebooks();

  const selectedNotebook = notebooks.find((n) => n.id === selectedNotebookId);

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <DatasetsNotebooksLeftBar
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>

        <ExplorersAndConvertersProvider>
          {selectedNotebookId ? (
            <TourProvider
              tourKey={TOUR_KEYS.NOTEBOOK}
              disabled={step !== 0}
              disabledMessage={t("datasets:label.tourDisabledMessage")}
            >
              <>
                <CenterPanel>
                  <DatasetsCenterContent />
                </CenterPanel>
                <RightPanel toggleButtonTop="50%">
                  {rightBarContent ? (
                    rightBarContent
                  ) : (
                    <RightBar
                      notebook={selectedNotebook}
                      onToggle={threePanelLayout.handleToggleRight}
                    />
                  )}
                </RightPanel>
              </>
            </TourProvider>
          ) : selectedDatasetId ? (
            <TourProvider
              tourKey={TOUR_KEYS.DATASET_VIEW}
              disabled={step !== 0}
              disabledMessage={t("datasets:label.tourDisabledMessageNotebook")}
            >
              <>
                <CenterPanel>
                  <DatasetsCenterContent />
                </CenterPanel>
                <RightPanel toggleButtonTop="50%">
                  {rightBarContent ? (
                    rightBarContent
                  ) : (
                    <RightBar
                      notebook={null}
                      onToggle={threePanelLayout.handleToggleRight}
                    />
                  )}
                </RightPanel>
              </>
            </TourProvider>
          ) : (
            <TourProvider
              tourKey={TOUR_KEYS.DATASETS}
              disabled={step !== 0}
              disabledMessage={t("datasets:label.tourDisabledMessage")}
            >
              <>
                <CenterPanel>
                  <DatasetsCenterContent />
                </CenterPanel>
                <RightPanel toggleButtonTop="50%">
                  {rightBarContent ? (
                    rightBarContent
                  ) : (
                    <RightBar
                      notebook={null}
                      onToggle={threePanelLayout.handleToggleRight}
                    />
                  )}
                </RightPanel>
              </>
            </TourProvider>
          )}
        </ExplorersAndConvertersProvider>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
