import { Box, Divider, Typography, IconButton } from "@mui/material";
import { ChevronLeft } from "@mui/icons-material";
import Footer from "../threeSectionLayout/Footer";
import BarHeader from "../threeSectionLayout/BarHeader";
import SideBar from "../threeSectionLayout/SideBar";

export default function ModelsLeftBar({ onToggle }) {
  return (
    <SideBar>
      {/* Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          pr: 2,
        }}
      >
        <BarHeader />
        <IconButton
          size="small"
          onClick={onToggle}
          sx={{ color: "text.secondary" }}
        >
          <ChevronLeft />
        </IconButton>
      </Box>
      <Divider sx={{ width: "100%", bgcolor: "#252836" }} />

      {/* Placeholder content */}
      <Box p={2} sx={{ height: "64px", display: "flex", alignItems: "center" }}>
        <Typography variant="body1" color="textSecondary">
          Models Module
        </Typography>
      </Box>

      <Divider sx={{ width: "90%", bgcolor: "#252836", mx: "auto" }} />

      {/* Scrollable content area */}
      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        <Box p={2}>
          <Typography variant="body2" color="text.secondary">
            Model sessions will appear here
          </Typography>
        </Box>
      </Box>

      {/* Footer */}
      <Footer />
    </SideBar>
  );
}
