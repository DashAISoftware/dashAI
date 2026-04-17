import { useEffect } from "react";
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
import { useTourContext } from "../../components/tour/TourProvider";
import { useGenerative } from "../../components/generative/GenerativeContext";
import { useTranslation } from "react-i18next";

export default function GenerativeContent() {
  const threePanelLayout = useThreePanelLayout({ storageKey: "generative" });
  const { stepIndex, selectedSessionId } = useGenerative();
  const { setDisabled } = useTourContext() ?? {};
  const { t } = useTranslation(["generative"]);

  useEffect(() => {
    setDisabled?.(
      stepIndex !== 0 || !!selectedSessionId,
      t("generative:label.tourDisabledMessage"),
    );
  }, [stepIndex, selectedSessionId, setDisabled, t]);

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel data-tour="sessions-left-panel">
          <SessionBar onToggle={threePanelLayout.handleToggleLeft} />
        </LeftPanel>
        <CenterPanel data-tour="task-gallery">
          {selectedSessionId ? (
            <GenerativeChat />
          ) : stepIndex === 0 ? (
            <SelectTaskMenu />
          ) : (
            <SelectModelMenu />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%" data-tour="parameters-right-panel">
          <ParamsBar onToggle={threePanelLayout.handleToggleRight} />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
