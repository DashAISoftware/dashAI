import React, { useState } from "react";
import { Box, Button, Typography, Tooltip } from "@mui/material";
import ConfigureToolModal from "../ConfigureToolModal";
import FormExplorerSection from "./FormExplorerSection";
import { useTourContext } from "../../tour/TourProvider";

export default function ExplorerList({
  explorers,
  hoveredTool,
  setHoveredTool,
}) {
  const [open, setOpen] = useState(false);
  const [selectedExplorer, setSelectedExplorer] = useState(null);
  const tourContext = useTourContext();

  const handleExplorerClick = (explorer) => {
    setSelectedExplorer(explorer);
    setOpen(true);

    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }

  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {explorers.length === 0 ? (
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            textAlign: "center",
            py: 2,
          }}
        >
          No explorations found matching your search.
        </Typography>
      ) : (
        explorers.map((exploration) => {
          const getTourAttribute = () => {
            if (exploration.name === "HistogramPlotExplorer") {
              return "histogram-explorer";
            }
            return null;
          };

          const tourAttr = getTourAttribute();

          const ButtonComponent = (
            <Button
              key={exploration.name}
              variant="contained"
              disabled={exploration.disabled}
              data-tour={tourAttr || undefined}
              sx={{
                width: "100%",
                minHeight: 48,
                bgcolor: exploration.disabled
                  ? "#1a1a1a"
                  : hoveredTool === exploration.type
                    ? "#444"
                    : "#333",
                color: exploration.disabled ? "#666" : "white",
                justifyContent: "flex-start",
                textTransform: "none",
                fontWeight: "normal",
                py: 1.5,
                px: 2,
                cursor: exploration.disabled ? "not-allowed" : "pointer",
                "&:hover": {
                  bgcolor: exploration.disabled ? "#1a1a1a" : "#444",
                },
                "&.Mui-disabled": {
                  color: "#666",
                  bgcolor: "#1a1a1a",
                  minHeight: 48,
                },
              }}
              onMouseEnter={() =>
                !exploration.disabled && setHoveredTool(exploration)
              }
              onMouseLeave={() => !exploration.disabled && setHoveredTool(null)}
              onClick={() =>
                !exploration.disabled && handleExplorerClick(exploration)
              }
            >
              {exploration.display_name}
            </Button>
          );

          if (exploration.disabled && exploration.tooltip) {
            return (
              <Tooltip
                key={exploration.name}
                title={exploration.tooltip}
                placement="left"
                arrow
              >
                <Box sx={{ width: "100%" }}>{ButtonComponent}</Box>
              </Tooltip>
            );
          }

          return ButtonComponent;
        })
      )}

      {selectedExplorer && (
        <ConfigureToolModal
          open={open}
          handleClose={() => {
            setOpen(false);
            setSelectedExplorer(null);
          }}
          tool={selectedExplorer}
          notebook={selectedExplorer.notebook}
          FormSection={FormExplorerSection}
        />
      )}
    </Box>
  );
}