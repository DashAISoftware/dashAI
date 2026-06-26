import React, { useState, useMemo, useEffect } from "react";
import {
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ToolListItem from "./ToolListItem";
import ConfigureToolModal from "./ConfigureToolModal";
import { useTourContext } from "../../tour/TourProvider";
import { groupByCategory, sortCategories } from "./toolCategories";
import { useTranslation } from "react-i18next";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";

export default function ToolList({ tools, notebook, FormComponent }) {
  const theme = useTheme();
  const [open, setOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets", "common"]);
  const { pendingDropTool, setPendingDropTool } = useExplorersAndConverters();

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

  useEffect(() => {
    if (!pendingDropTool) return;
    const match = tools.find((t) => t.name === pendingDropTool.name);
    if (match) {
      handleToolClick(match);
      setPendingDropTool(null);
    }
  }, [pendingDropTool, tools]);

  if (!tools || tools.length === 0) {
    return (
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", textAlign: "center", py: 4 }}
      >
        {t("datasets:label.noToolsMatched")}
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 3,
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
              bgcolor: theme.palette.ui.box,
              borderRadius: 1.5,
              overflow: "hidden",
              "&:before": { display: "none" },
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ color: "text.secondary" }} />}
              sx={{
                px: 3,
                py: 2,
                minHeight: "auto",
                "& .MuiAccordionSummary-content": {
                  alignItems: "center",
                  gap: 2,
                  my: 2,
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
                  bgcolor: theme.palette.ui.disabled,
                  color: "text.secondary",
                  height: 20,
                }}
              />
            </AccordionSummary>
            <AccordionDetails sx={{ px: 3, pb: 3 }}>
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 3,
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
