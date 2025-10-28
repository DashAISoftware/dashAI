import React, { useState } from "react";
import { Box, Grid } from "@mui/material";
import ToolGridItem from "./ToolGridItem";
import ConfigureToolModal from "./ConfigureToolModal";
import { useTourContext } from "../../tour/TourProvider";

export default function ToolGrid({ tools, notebook, FormComponent }) {
  const [open, setOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState(null);
  const tourContext = useTourContext();

  const handleToolClick = (tool) => {
    setSelectedTool(tool);
    setOpen(true);

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

  return (
    <>
      <Grid container spacing={2}>
        {tools.map((item) => (
          <Grid item xs={12} sm={6} md={4} key={item.name}>
            <ToolGridItem
              tool={item}
              disabled={item.disabled}
              onClick={() => handleToolClick(item)}
            />
          </Grid>
        ))}
      </Grid>
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
    </>
  );
}
