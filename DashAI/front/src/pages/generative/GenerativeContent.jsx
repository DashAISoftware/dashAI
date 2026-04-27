import { useEffect } from "react";
import { useLocation, useParams } from "react-router-dom";
import { Box } from "@mui/material";
import ModuleContainer from "../../components/layout/ModuleContainer";
import LeftPanel from "../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../components/generative/SessionBar";
import SelectTaskMenu from "../../components/generative/SelectTaskMenu";
import GenerativeChat from "../../components/generative/GenerativeChat";
import SelectModelMenu from "../../components/generative/SelectModelMenu";
import ParamsBar from "../../components/generative/ParamsBar";
import GenerativeBreadcrumbs from "../../components/generative/GenerativeBreadcrumbs";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { useTourContext } from "../../components/tour/TourProvider";
import { useGenerative } from "../../components/generative/GenerativeContext";
import { useTranslation } from "react-i18next";

export default function GenerativeContent() {
  const threePanelLayout = useThreePanelLayout({ storageKey: "generative" });
  const location = useLocation();
  const params = useParams();
  const {
    stepIndex,
    selectedSessionId,
    setSelectedSessionId,
    setSelectedTaskName,
    setSelectedDisplayName,
    setStepIndex,
    sessions,
    tasks,
  } = useGenerative();
  const { setDisabled } = useTourContext() ?? {};
  const { t } = useTranslation(["generative"]);

  useEffect(() => {
    const path = location.pathname;

    if (path.startsWith("/app/generative/sessions/new/") && params.taskName) {
      const task = tasks.find((tk) => tk.name === params.taskName);
      setSelectedTaskName(params.taskName);
      setSelectedDisplayName(task?.display_name ?? null);
      setSelectedSessionId(null);
      setStepIndex(1);
      return;
    }

    if (path.startsWith("/app/generative/sessions/") && params.id) {
      const id = Number(params.id);
      const session = sessions.find((s) => s.id === id);
      if (session) {
        const task = tasks.find((tk) => tk.name === session.task_name);
        setSelectedTaskName(session.task_name);
        setSelectedDisplayName(task?.display_name ?? null);
      }
      setSelectedSessionId(id);
      setStepIndex(0);
      return;
    }

    if (path === "/app/generative" || path === "/app/generative/") {
      setSelectedSessionId(null);
      setSelectedTaskName("");
      setSelectedDisplayName(null);
      setStepIndex(0);
    }
  }, [location.pathname, params.id, params.taskName, tasks, sessions]);

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
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                width: "100%",
                height: "100%",
                overflow: "auto",
                px: 2,
                pt: 2,
              }}
            >
              <GenerativeBreadcrumbs />
              <SelectModelMenu />
            </Box>
          )}
        </CenterPanel>

        <RightPanel toggleButtonTop="50%" data-tour="parameters-right-panel">
          <ParamsBar onToggle={threePanelLayout.handleToggleRight} />
        </RightPanel>
      </ModuleContainer>
    </ThreePanelLayoutContext.Provider>
  );
}
