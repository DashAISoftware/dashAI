import React from "react";
import { Box, Typography } from "@mui/material";
import JobQueueWidget from "../jobs/JobQueueWidget";

export default function SessionVisualization({ session }) {
  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          justifyContent: "center",
          alignItems: "center",
          p: 4,
        }}
      >
        <Typography variant="h5" color="text.secondary">
          Session Visualization
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 2 }}>
          Content coming soon...
        </Typography>
        {session && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Session: {session.name}
          </Typography>
        )}
      </Box>
      <JobQueueWidget />
    </>
  );
}
