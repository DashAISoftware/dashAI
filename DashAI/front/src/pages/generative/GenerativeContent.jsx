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
import { getSessions, removeSession } from "../../api/session";
import { getComponents } from "../../api/component";
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
    setSelectedDisplayName,
    setSessions,
    setParamsVersion,
  } = useGenerative();

  const handleSessionClick = (sessionId, taskName, taskDisplayName) => {
    setSelectedTaskName(taskName);
    setSelectedSessionId(sessionId);
    setSelectedDisplayName(taskDisplayName);
  };

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

  const handleSessionDelete = (id) => {
    if (id === selectedSessionId) {
      setSelectedSessionId(null);
      setStepIndex(0);
    }

    setSessions((prevSessions) =>
      prevSessions.filter((session) => session.id !== id),
    );

    removeSession(id);
  };

  return (
    <ThreePanelLayoutContext.Provider value={threePanelLayout}>
      <ModuleContainer>
        <LeftPanel>
          <SessionBar
            handleSessionClick={handleSessionClick}
            handleNewSessionButton={handleNewSessionButton}
            handleSessionDelete={handleSessionDelete}
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
