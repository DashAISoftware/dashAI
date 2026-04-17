import React from "react";
import ModuleContainer from "../layout/ModuleContainer";
import LeftPanel from "../threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../threeSectionLayout/panels/CenterPanel";
import RightPanel from "../threeSectionLayout/panels/RightPanel";
import { useThreePanelLayout } from "../../hooks/useThreePanelsLayout";
import { ThreePanelLayoutContext } from "../threeSectionLayout/panels/ThreePanelLayoutContext";
import CustomComponentsLeftBar from "./CustomComponentsLeftBar";
import CustomComponentsCenter from "./CustomComponentsCenter";
import CustomComponentsRightBar from "./CustomComponentsRightBar";
import { CustomComponentsProvider } from "./CustomComponentsContext";

export default function CustomComponentsContent() {
  const threePanelLayout = useThreePanelLayout({
    storageKey: "customComponents",
  });

  return (
    <CustomComponentsProvider>
      <ThreePanelLayoutContext.Provider value={threePanelLayout}>
        <ModuleContainer>
          <LeftPanel>
            <CustomComponentsLeftBar />
          </LeftPanel>
          <CenterPanel>
            <CustomComponentsCenter />
          </CenterPanel>
          <RightPanel toggleButtonTop="50%">
            <CustomComponentsRightBar />
          </RightPanel>
        </ModuleContainer>
      </ThreePanelLayoutContext.Provider>
    </CustomComponentsProvider>
  );
}
