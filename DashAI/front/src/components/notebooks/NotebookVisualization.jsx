import React from "react";
import {
  Box,
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Typography,
  Divider,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import NotebookView from "./NotebookView";

export default function NotebookVisualization({ notebook }) {
  return (
    <Box>
      {/* Dataset view */}
      <Box
        sx={{
          mb: 2,
        }}
      >
        <Typography variant="h5" my={2}>
          Dataset Preview
        </Typography>
        <Accordion
          width="100%"
          sx={{ bgcolor: "#212121", borderRadius: 2, boxShadow: "none" }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="panel1-content"
            id="panel1-header"
          >
            <Typography component="span">Iris</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box>Dataset Component </Box>
          </AccordionDetails>
        </Accordion>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* Notebook view */}
      <Box mt={2}>
        <NotebookView notebook={notebook} />
      </Box>
    </Box>
  );
}
