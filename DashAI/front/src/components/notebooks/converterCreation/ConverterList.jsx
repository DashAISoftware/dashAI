import React, { useMemo, useState } from "react";
import {
  Box,
  Button,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ConfigureToolModal from "../ConfigureToolModal";
import FormConverterSection from "./FormConverterSection";

/**
 * Utility: group converters by category.
 * Falls back to "Other" when category is missing.
 */
function groupByCategory(converters) {
  const groups = converters.reduce((acc, c) => {
    const cat = c?.metadata?.category || "Other";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(c);
    return acc;
  }, {});
  return groups;
}

const PREFERRED_ORDER = [
  "Basic Preprocessing",
  "Encoding",
  "Scaling & Normalization",
  "Dimensionality Reduction",
  "Feature Selection",
  "Polynomial & Kernel Methods",
  "Resampling & Class Balancing",
  "Pipelines & Meta-Converters",
  "Advanced / Specialized",
  "Other",
];

function sortCategories(catNames) {
  const set = new Set(PREFERRED_ORDER);
  const preferred = catNames.filter((c) => set.has(c));
  const remaining = catNames.filter((c) => !set.has(c)).sort();
  return [
    ...PREFERRED_ORDER.filter((c) => preferred.includes(c)),
    ...remaining,
  ];
}

export default function ConverterList({
  converters,
  hoveredTool,
  setHoveredTool,
  notebook,
}) {
  const [open, setOpen] = useState(false);
  const [selectedConverter, setSelectedConverter] = useState(null);

  const grouped = useMemo(() => groupByCategory(converters), [converters]);
  const categories = useMemo(
    () => sortCategories(Object.keys(grouped)),
    [grouped],
  );

  const handleConverterClick = (converter) => {
    setSelectedConverter(converter);
    setOpen(true);
  };

  if (!converters || converters.length === 0) {
    return (
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", textAlign: "center", py: 2 }}
      >
        No converters found matching your search.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {categories.map((cat) => {
        const list = grouped[cat] || [];
        return (
          <Accordion
            key={cat}
            disableGutters
            sx={{
              bgcolor: "#1f1f1f",
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
                "& .MuiAccordionSummary-content": {
                  alignItems: "center",
                  gap: 1,
                },
              }}
            >
              <Typography variant="subtitle2" sx={{ flex: 1 }}>
                {cat}
              </Typography>
              <Chip
                size="small"
                label={list.length}
                sx={{ bgcolor: "#2b2b2b", color: "text.secondary" }}
              />
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 1 }}
            >
              {list
                .slice()
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((converter) => {
                  const displayName = converter.name;
                  return (
                    <Button
                      key={converter.name}
                      variant="contained"
                      sx={{
                        bgcolor:
                          hoveredTool?.name === converter.name
                            ? "#444"
                            : "#333",
                        color: "white",
                        justifyContent: "flex-start",
                        textTransform: "none",
                        fontWeight: "normal",
                        py: 1.5,
                        "&:hover": { bgcolor: "#444" },
                      }}
                      onMouseEnter={() => setHoveredTool(converter)}
                      onMouseLeave={() => setHoveredTool(null)}
                      onClick={() => handleConverterClick(converter)}
                    >
                      {displayName}
                    </Button>
                  );
                })}
            </AccordionDetails>
          </Accordion>
        );
      })}

      {selectedConverter && (
        <ConfigureToolModal
          open={open}
          handleClose={() => {
            setOpen(false);
            setSelectedConverter(null);
          }}
          tool={selectedConverter}
          notebook={notebook}
          FormSection={FormConverterSection}
        />
      )}
    </Box>
  );
}
