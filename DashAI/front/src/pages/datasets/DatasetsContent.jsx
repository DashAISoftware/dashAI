import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import DatasetsNotebooksLeftBar from "../../components/notebooks/DatasetNotebookLeftBar";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightBar from "../../components/notebooks/RightBar";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import DatasetsCenterContent from "../../components/notebooks/dataset/DatasetsCenterContent";
import { TourProvider } from "../../components/tour/TourProvider";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import { ExplorersAndConvertersProvider } from "../../components/notebooks/context/ExplorersAndConvertersContext";
import { useTranslation } from "react-i18next";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useDatasetsAndNotebooks } from "../../components/custom/contexts/DatasetsAndNotebooksContext";

export default function DatasetsContent() {
  const { t } = useTranslation(["datasets", "common"]);
  const threePanelLayout = useThreePanelLayout();

  const { notebooks, selectedNotebookId, rightBarContent } =
    useDatasetsAndNotebooks();

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
            <TourProvider tourKey={TOUR_KEYS.NOTEBOOK}>
              <>
                <CenterPanel>
                  <DatasetsCenterContent t={t} />
                </CenterPanel>
                <RightPanel toggleButtonTop="calc(50% + 60px)">
                  {rightBarContent ? (
                    rightBarContent
                  ) : (
                    <RightBar
                      notebook={selectedNotebook}
                      onToggle={threePanelLayout.handleToggleRight}
                    />
                  )}
                </RightPanel>
                <TourButton tourKey={TOUR_KEYS.NOTEBOOK} />
              </>
            </TourProvider>
          ) : (
            <>
              <CenterPanel>
                <DatasetsCenterContent t={t} />
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
          )}
        </ExplorersAndConvertersProvider>
      </ModuleContainer>
      {!selectedNotebookId && <TourButton tourKey={TOUR_KEYS.DATASETS} />}
    </ThreePanelLayoutContext.Provider>
  );
}
