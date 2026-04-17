import { Box, IconButton } from "@mui/material";
import { ChevronLeft, ChevronRight } from "@mui/icons-material";
import { useThreePanelLayoutContext } from "./ThreePanelLayoutContext";
export default function RightPanel({
  toggleButtonTop = "50%",
  children,
  "data-tour": dataTour,
}) {
  const {
    rightBarVisible,
    rightBarWidth,
    isTogglingRight,
    bindRightResize,
    handleToggleRight,
  } = useThreePanelLayoutContext();
  return (
    <>
      <IconButton
        onClick={handleToggleRight}
        size="small"
        sx={{
          position: "absolute",
          right: rightBarVisible ? `calc(${rightBarWidth}% - 9px)` : 8,
          top: toggleButtonTop,
          transform: "translateY(-50%)",
          bgcolor: "primary.main",
          color: "primary.contrastText",
          border: "1px solid",
          borderColor: "primary.dark",
          boxShadow: 2,
          width: 18,
          height: 32,
          borderRadius: 1,
          zIndex: 11,
          transition: isTogglingRight
            ? "right 0.3s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.2s ease, transform 0.2s ease"
            : "background-color 0.2s ease, transform 0.2s ease",
          "&:hover": {
            bgcolor: "primary.light",
            transform: "translateY(-50%) scale(1.1)",
          },
        }}
      >
        {rightBarVisible ? (
          <ChevronRight fontSize="small" />
        ) : (
          <ChevronLeft fontSize="small" />
        )}
      </IconButton>
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
        data-tour={dataTour}
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
