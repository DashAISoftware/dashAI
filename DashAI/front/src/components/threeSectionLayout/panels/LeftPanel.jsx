import { Box, IconButton } from "@mui/material";
import { ChevronRight } from "@mui/icons-material";
import { useThreePanelLayoutContext } from "./ThreePanelLayoutContext";

export default function LeftPanel({ children }) {
  const {
    leftBarVisible,
    leftBarWidth,
    isTogglingLeft,
    bindLeftResize,
    handleToggleLeft,
  } = useThreePanelLayoutContext();
  return (
    <>
      {!leftBarVisible && (
        <IconButton
          onClick={handleToggleLeft}
          sx={{
            position: "absolute",
            left: 8,
            top: "50%",
            transform: "translateY(-50%)",
            bgcolor: "background.paper",
            zIndex: 10,
            transition: "all 0.2s ease",
            "&:hover": {
              bgcolor: "action.hover",
              transform: "translateY(-50%) scale(1.1)",
            },
          }}
        >
          <ChevronRight />
        </IconButton>
      )}
      <Box
        width={leftBarVisible ? `${leftBarWidth}%` : "0%"}
        position="relative"
        className="datasets-list"
        sx={{
          transition: isTogglingLeft
            ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease"
            : "none",
          opacity: leftBarVisible ? 1 : 0,
          overflow: "hidden",
        }}
      >
        {leftBarVisible && (
          <>
            {children}
            <Box
              {...bindLeftResize}
              sx={{
                position: "absolute",
                right: -2,
                top: 0,
                bottom: 0,
                width: "5px",
                cursor: "col-resize",
                bgcolor: "transparent",
                transition: "background-color 0.2s ease",
                "&:hover": {
                  bgcolor: "primary.main",
                },
                zIndex: 10,
              }}
            />
          </>
        )}
      </Box>
    </>
  );
}
