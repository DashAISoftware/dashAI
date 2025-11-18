import React, { useState } from "react";
import {
  Box,
  Typography,
  Divider,
  Stack,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";

import GeneralForm from "./forms/GeneralForm";
import TraceForm from "./forms/TraceForm";
import XAxisForm from "./forms/XAxisForm";
import YAxisForm from "./forms/YAxisForm";
import LegendForm from "./forms/LegendForm";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

export default function PlotLayoutForm({
  data,
  setData,
  layout,
  setLayout,
  onSave,
}) {
  if (!layout) return null;

  const [modified, setModified] = useState(false);
  const [localLayout, setLocalLayout] = useState(structuredClone(layout));
  const [localData, setLocalData] = useState(structuredClone(data));

  const handleTraceChange = (index, path, value) => {
    const newData = [...data];
    const newTrace = structuredClone(newData[index]);

    const keys = path.split(".");
    let obj = newTrace;
    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i];
      obj[k] = obj[k] || {};
      obj = obj[k];
    }
    obj[keys[keys.length - 1]] = value;

    newData[index] = newTrace;
    setData(newData);
    setModified(true);
  };

  const handleChange = (field, value) => {
    setLayout({ ...layout, [field]: value });
    setModified(true);
  };

  const handleCancel = () => {
    setLayout(structuredClone(localLayout));
    setData(structuredClone(localData));
    setModified(false);
  };

  const handleSave = () => {
    setLocalData(structuredClone(data));
    setLocalLayout(structuredClone(layout));
    setModified(false);
    onSave();
  };

  const handleAxisChange = (axis, field, value) => {
    setLayout({
      ...layout,
      [axis]: { ...layout[axis], [field]: value },
    });
    setModified(true);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        width: "100%",
        bgcolor: "#1e1e1e",
        color: "white",
        p: 3,
        borderRadius: 2,
        boxShadow: 2,
      }}
    >
      <Typography variant="h6" sx={{ mb: 1 }}>
        Edit Plot Layout
      </Typography>

      {/* General Settings */}
      <Accordion defaultExpanded sx={{ bgcolor: "#2a2a2a", color: "white" }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight="bold">
            General Settings
          </Typography>
        </AccordionSummary>
        <AccordionDetails
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <GeneralForm layout={layout} handleChange={handleChange} />
        </AccordionDetails>
      </Accordion>

      {/* Trace Settings */}
      {Array.isArray(data) &&
        data.map((trace, index) => (
          <Accordion key={index} sx={{ bgcolor: "#2a2a2a", color: "white" }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="bold">
                Trace {index + 1} ({trace.name || trace.type})
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <TraceForm
                layout={layout}
                trace={trace}
                index={index}
                handleTraceChange={handleTraceChange}
                handleChange={handleChange}
              />
            </AccordionDetails>
          </Accordion>
        ))}

      {/* X Axis Settings */}
      <Accordion sx={{ bgcolor: "#2a2a2a", color: "white" }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight="bold">
            X Axis
          </Typography>
        </AccordionSummary>
        <AccordionDetails
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <XAxisForm layout={layout} handleAxisChange={handleAxisChange} />
        </AccordionDetails>
      </Accordion>

      {/* Y Axis Settings */}
      <Accordion sx={{ bgcolor: "#2a2a2a", color: "white" }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight="bold">
            Y Axis
          </Typography>
        </AccordionSummary>
        <AccordionDetails
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <YAxisForm layout={layout} handleAxisChange={handleAxisChange} />
        </AccordionDetails>
      </Accordion>

      {/* Legend Settings */}
      <Accordion sx={{ bgcolor: "#2a2a2a", color: "white" }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight="bold">
            Legend
          </Typography>
        </AccordionSummary>
        <AccordionDetails
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <LegendForm layout={layout} handleChange={handleChange} />
        </AccordionDetails>
      </Accordion>

      <Divider sx={{ my: 2, borderColor: "#444" }} />

      <Stack direction="row" spacing={2} justifyContent="flex-end">
        <Button variant="outlined" onClick={handleCancel} disabled={!modified}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSave}
          disabled={!modified}
        >
          Save
        </Button>
      </Stack>
    </Box>
  );
}
