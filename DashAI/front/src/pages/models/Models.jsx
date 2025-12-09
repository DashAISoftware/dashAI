import React from "react";
import { Typography, Box } from "@mui/material";
import CustomLayout from "../../components/custom/CustomLayout";

export default function Models() {
  return (
    <CustomLayout>
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Models
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Configure tasks, train and compare models in organized sessions.
        </Typography>
        <Typography variant="body1" color="text.secondary">
          This section is under development.
        </Typography>
      </Box>
    </CustomLayout>
  );
}
