import { Box, IconButton } from "@mui/material";
import { ChevronLeft } from "@mui/icons-material";
import { useThreePanelLayoutContext } from "./ThreePanelLayoutContext";

export default function RightPanel({ isNotebook, children }) {
  const {
    rightBarVisible,
    rightBarWidth,
    isTogglingRight,
    bindRightResize,
    handleToggleRight,
  } = useThreePanelLayoutContext();
  return (
    <>
      {!rightBarVisible && (
        <IconButton
          onClick={handleToggleRight}
          sx={{
            position: "absolute",
            right: 8,
            top: isNotebook ? "calc(50% + 60px)" : "50%",
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
          <ChevronLeft />
        </IconButton>
      )}
      <Box
        width={rightBarVisible ? `${rightBarWidth}%` : "0%"}
        position="relative"
        sx={{
          transition: isTogglingRight
            ? "width 0.3s cubic-bezier(0.4, 0, 0.2, 1), margin 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease"
            : "none",
          opacity: rightBarVisible ? 1 : 0,
          overflow: "hidden",
        }}
      >
        {rightBarVisible && (
          <>
            <Box
              {...bindRightResize}
              sx={{
                position: "absolute",
                left: -2,
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
            {children}
          </>
        )}
      </Box>
    </>
  );
}
