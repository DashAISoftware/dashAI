export const getTourStyles = (theme) => ({
  options: {
    arrowColor: theme.palette.background.paper,
    backgroundColor: theme.palette.background.paper,
    beaconSize: 36,
    overlayColor: "rgba(0, 0, 0, 0.5)",
    primaryColor: theme.palette.primary.main,
    spotlightShadow: "none",
    textColor: theme.palette.text.primary,
    width: 280,
    zIndex: 10000,
  },
  beacon: {
    animation: "pulse 2s infinite",
  },
});
