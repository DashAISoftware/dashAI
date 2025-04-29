import { Dialog, IconButton, Fade, Zoom, Box, useTheme } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

export function FullscreenImageChat({ open, onClose, imageData }) {
  const theme = useTheme();

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xl"
      fullWidth
      TransitionComponent={Fade}
      transitionDuration={{
        enter: theme.transitions.duration.enteringScreen,
        exit: theme.transitions.duration.leavingScreen,
      }}
      PaperProps={{
        sx: {
          backgroundColor: "rgba(0, 0, 0, 0.9)",
          boxShadow: "none",
          position: "relative",
          m: 0,
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        },
      }}
    >
      <IconButton
        onClick={onClose}
        sx={{
          position: "absolute",
          top: theme.spacing(2),
          right: theme.spacing(2),
          color: "white",
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          "&:hover": {
            backgroundColor: "rgba(0, 0, 0, 0.7)",
          },
          zIndex: 1,
        }}
        aria-label="close"
        size="large"
      >
        <CloseIcon />
      </IconButton>

      <Zoom in={open}>
        <Box
          component="img"
          src={imageData ? `data:image/png;base64,${imageData}` : ""}
          alt="Fullscreen Image"
          sx={{
            maxWidth: "90%",
            maxHeight: "90%",
            objectFit: "contain",
            cursor: "pointer",
          }}
          onClick={onClose}
        />
      </Zoom>
    </Dialog>
  );
}
