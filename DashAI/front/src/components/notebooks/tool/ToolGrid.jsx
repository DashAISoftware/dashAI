import React, { useState, useMemo } from "react";
import { Box, Typography } from "@mui/material";
import ToolGridItem from "./ToolGridItem";
import ConfigureToolModal from "./ConfigureToolModal";
import { useTourContext } from "../../tour/TourProvider";
import { groupByCategory, sortCategories } from "./toolCategories";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

export default function ToolGrid({ tools, notebook, FormComponent }) {
  const [open, setOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets", "common"]);
  const theme = useTheme();

  const grouped = useMemo(() => groupByCategory(tools), [tools]);
  const categories = useMemo(
    () => sortCategories(Object.keys(grouped)),
    [grouped],
  );

  const handleToolClick = (tool) => {
    setSelectedTool(tool);
    setOpen(true);

    // Auto-advance tour for specific tools
    if (tourContext && tourContext.run) {
      const shouldAdvance =
        tool.name === "HistogramPlotExplorer" ||
        tool.name === "LabelEncoder" ||
        tool.name === "NanRemover";

      if (shouldAdvance) {
        setTimeout(() => {
          tourContext.nextStep();
        }, 500);
      }
    }
  };

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
    <Box sx={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {categories.map((cat) => {
        const list = grouped[cat] || [];
        return (
          <Box key={cat}>
            {/* Category Header */}
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 2,
                mb: 3,
                pb: 1,
                borderBottom: "1px solid",
                borderColor: theme.palette.divider,
              }}
            >
              <Typography
                variant="subtitle2"
                sx={{ flex: 1, color: "text.primary" }}
              >
                {cat}
              </Typography>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                {t("datasets:label.toolsCount", { count: list.length })}
              </Typography>
            </Box>

            {/* Grid of tools */}
            <Box
              sx={{
                display: "grid",
                gap: 3,
                gridTemplateColumns: {
                  lg: "repeat(1, minmax(0, 1fr))",
                  xl: "repeat(2, minmax(0, 1fr))",
                },
                width: "100%",
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
                  <ToolGridItem
                    key={tool.name}
                    tool={tool}
                    disabled={tool.disabled}
                    onClick={() => handleToolClick(tool)}
                  />
                ))}
            </Box>
          </Box>
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
