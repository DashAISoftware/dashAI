import { IconButton, Tooltip } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { useTourContext } from "./TourProvider";

export const TourButton = ({
  tourKey,
  disabled = false,
  disabledMessage = "Tour not available",
}) => {
  const { resetTour, startTour } = useTourContext();
  return (
    <Tooltip title={disabled ? disabledMessage : "Start Tour"} placement="left">
      <IconButton
        onClick={() => {
          if (!disabled) {
            resetTour();
            startTour();
          }
        }}
        sx={{
          position: "fixed",
          top: 64,
          right: 16,
          backgroundColor: disabled ? "#9e9e9e" : "#1976d2",
          color: "white",
          width: 36,
          height: 36,
          "&:hover": {
            backgroundColor: disabled ? "#9e9e9e" : "#1565c0",
            transform: disabled ? "none" : "scale(1.05)",
          },
          transition: "all 0.2s ease-in-out",
          boxShadow: 2,
          zIndex: 9000,
          opacity: disabled ? 0.6 : 1,
          cursor: disabled ? "not-allowed" : "pointer",
          pointerEvents: "auto",
        }}
      >
        <HelpOutlineIcon />
      </IconButton>
    </Tooltip>
  );
};
