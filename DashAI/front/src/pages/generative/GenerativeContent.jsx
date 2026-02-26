import { Box } from "@mui/material";
import { useState, useEffect } from "react";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../components/generative/SessionBar";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import { removeSession } from "../../api/session";
import { useTranslation } from "react-i18next";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { TourButton } from "../../components/tour/TourButton";
import { TOUR_KEYS } from "../../constants/tours";
import { useGenerative } from "../../components/generative/GenerativeContext";

export default function GenerativeContent() {
  const { t } = useTranslation(["generative", "common"]);
  const threePanelLayout = useThreePanelLayout();

  const {
    stepIndex,
    setStepIndex,
    selectedSessionId,
    setSelectedSessionId,
    setSelectedTaskName,
    setSessions,
    setParamsVersion,
  } = useGenerative();

  const handleNewSessionButton = () => {
    setSelectedSessionId(null);
    setStepIndex(0);
    setSelectedTaskName("");
  };

  const onParamsUpdate = (newParams) => {
    setParamsVersion((prev) => prev + 1);
  };

  const handleAddSession = (session) => {
    setSessions((prevSessions) => [...prevSessions, session]);
  };

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <SessionBar
            handleNewSessionButton={handleNewSessionButton}
            onToggle={threePanelLayout.handleToggleLeft}
          />
        </LeftPanel>
        <CenterPanel>
          {selectedSessionId ? (
            <GenerativeChat />
          ) : stepIndex === 0 ? (
            <SelectTaskMenu />
          ) : (
            <SelectModelMenu handleAddSession={handleAddSession} />
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%">
          <ParamsBar
            onParamsUpdate={onParamsUpdate}
            onToggle={threePanelLayout.handleToggleRight}
          />
          <TourButton tourKey={TOUR_KEYS.GENERATIVE} />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
