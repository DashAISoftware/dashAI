import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../components/generative/SessionBar";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import { useGenerative } from "../../components/generative/GenerativeContext";

export default function GenerativeContent() {
  const threePanelLayout = useThreePanelLayout();
  const { stepIndex, selectedSessionId } = useGenerative();

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <SessionBar onToggle={threePanelLayout.handleToggleLeft} />
        </LeftPanel>
        <CenterPanel>
          {selectedSessionId ? (
            <GenerativeChat />
          ) : stepIndex === 0 ? (
            <SelectTaskMenu />
          ) : (
            <SelectModelMenu />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          <ParamsBar onToggle={threePanelLayout.handleToggleRight} />
          <TourButton tourKey={TOUR_KEYS.GENERATIVE} />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
