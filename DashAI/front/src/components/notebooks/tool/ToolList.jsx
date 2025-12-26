import React, { useState, useMemo } from "react";
import {
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ToolListItem from "./ToolListItem";
import ConfigureToolModal from "./ConfigureToolModal";
import { useTourContext } from "../../tour/TourProvider";
import { groupByCategory, sortCategories } from "./toolCategories";

export default function ToolList({ tools, notebook, FormComponent }) {
  const [open, setOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const tourContext = useTourContext();

  const grouped = useMemo(() => groupByCategory(tools), [tools]);
  const categories = useMemo(
    () => sortCategories(Object.keys(grouped)),
    [grouped],
  );

  const handleToolClick = (tool) => {
    setSelectedTool(tool);
    setOpen(true);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };

  if (!tools || tools.length === 0) {
    return (
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", textAlign: "center", py: 2 }}
      >
        No tools found matching your search.
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        minWidth: 0,
      }}
    >
      {categories.map((cat) => {
        const list = grouped[cat] || [];
        return (
          <Accordion
            key={cat}
            disableGutters
            defaultExpanded
            sx={{
              bgcolor: "rgb(31, 31, 31)",
              borderRadius: 1.5,
              overflow: "hidden",
              "&:before": { display: "none" },
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ color: "text.secondary" }} />}
              sx={{
                px: 1.5,
                py: 1,
                minHeight: "auto",
                "& .MuiAccordionSummary-content": {
                  alignItems: "center",
                  gap: 1,
                  my: 1,
                },
              }}
            >
              <Typography variant="subtitle2" sx={{ flex: 1 }}>
                {cat}
              </Typography>
              <Chip
                size="small"
                label={list.length}
                sx={{
                  bgcolor: "rgb(43, 43, 43)",
                  color: "text.secondary",
                  height: 20,
                }}
              />
            </AccordionSummary>
            <AccordionDetails sx={{ px: 1.5, pb: 1.5 }}>
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 1.5,
                }}
              >
                {list
                  .slice()
                  .sort((a, b) => {
                    const nameA = a.display_name || a.name;
                    const nameB = b.display_name || b.name;
                    return nameA.localeCompare(nameB);
                  })
                  .map((tool) => (
                    <ToolListItem
                      key={tool.name}
                      tool={tool}
                      disabled={tool.disabled}
                      onClick={() => handleToolClick(tool)}
                    />
                  ))}
              </Box>
            </AccordionDetails>
          </Accordion>
        );
      })}

      {selectedTool && (
        <ConfigureToolModal
          open={open}
          handleClose={() => {
            setOpen(false);
            setSelectedTool(null);
          }}
          tool={selectedTool}
          notebook={notebook}
          FormSection={FormComponent}
        />
      )}
    </Box>
  );
}
