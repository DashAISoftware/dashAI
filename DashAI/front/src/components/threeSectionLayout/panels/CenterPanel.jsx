import { Box } from "@mui/material";
import CenterBox from "../panelContainers/CenterBox";
import { useThreePanelLayoutContext } from "./ThreePanelLayoutContext";

export default function CenterPanel({ children }) {
  const { centerWidth, isTogglingLeft, isTogglingRight } =
    useThreePanelLayoutContext();
  return (
    <Box
      width={`${centerWidth}%`}
      sx={{
        transition:
          isTogglingLeft || isTogglingRight
            ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
            : "none",
      }}
    >
      <CenterBox>{children}</CenterBox>
    </Box>
  );
}
