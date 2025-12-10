import { Box, Typography, IconButton } from "@mui/material";
import { ChevronRight } from "@mui/icons-material";
import SideBar from "../threeSectionLayout/SideBar";

export default function ModelsRightBar({ session, onToggle }) {
  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          height: "100%",
          width: "100%",
        }}
      >
        <Box
          sx={{
            p: 2,
            borderBottom: "1px solid #333",
            flexShrink: 0,
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6">Models</Typography>
          <IconButton
            size="small"
            onClick={onToggle}
            sx={{ color: "text.secondary" }}
          >
            <ChevronRight />
          </IconButton>
        </Box>

        <Box
          sx={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            p: 2,
          }}
        >
          <Typography
            variant="body2"
            sx={{ color: "text.secondary", textAlign: "center" }}
          >
            {session
              ? "Model details will appear here"
              : "Select a session to view model details."}
          </Typography>
        </Box>
      </Box>
    </SideBar>
  );
}
