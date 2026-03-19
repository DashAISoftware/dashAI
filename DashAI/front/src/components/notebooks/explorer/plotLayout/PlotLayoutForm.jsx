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
  TextField,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";

import GeneralForm from "./forms/GeneralForm";
import TraceForm from "./forms/TraceForm";
import XAxisForm from "./forms/XAxisForm";
import YAxisForm from "./forms/YAxisForm";
import LegendForm from "./forms/LegendForm";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DimensionsForm from "./forms/DimensionsForm";
import { useTranslation } from "react-i18next";

export default function PlotLayoutForm({
  data,
  setData,
  layout,
  setLayout,
  onSave,
}) {
  const theme = useTheme();
  const [modified, setModified] = useState(false);
  const [localLayout, setLocalLayout] = useState(() =>
    layout ? structuredClone(layout) : null,
  );
  const [localData, setLocalData] = useState(() =>
    data ? structuredClone(data) : null,
  );
  const { t } = useTranslation(["datasets", "common"]);

  if (!layout) return null;

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
        bgcolor: theme.palette.background.paper,
        color: "text.primary",
        p: 3,
        borderRadius: 2,
        boxShadow: 2,
      }}
    >
      <Typography variant="h6" sx={{ mb: 1 }}>
        {t("datasets:label.editPlotLayout")}
      </Typography>

      {/* General Settings */}
      <Accordion
        defaultExpanded
        sx={{ bgcolor: theme.palette.ui.panelMedium, color: "text.primary" }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight="bold">
            {t("datasets:label.generalSettings")}
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
          <Accordion
            key={trace.name != null ? `trace-${trace.name}` : `trace-${index}`}
            sx={{
              bgcolor: theme.palette.ui.panelMedium,
              color: "text.primary",
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="bold">
                {t("datasets:label.traceIdx", {
                  index: index + 1,
                  trace: trace.name || trace.type,
                })}
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

      {data?.[0]?.dimensions ? (
        <Accordion
          sx={{ bgcolor: theme.palette.ui.panelMedium, color: "text.primary" }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" fontWeight="bold">
              {t("datasets:label.dimensionsLabels")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            sx={{ display: "flex", flexDirection: "column", gap: 2 }}
          >
            <DimensionsForm data={data} handleTraceChange={handleTraceChange} />
          </AccordionDetails>
        </Accordion>
      ) : (
        <>
          {/* X Axis Settings */}
          <Accordion
            sx={{
              bgcolor: theme.palette.ui.panelMedium,
              color: "text.primary",
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="bold">
                {t("datasets:label.xAxis")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <XAxisForm
                data={data}
                layout={layout}
                handleAxisChange={handleAxisChange}
                handleTraceChange={handleTraceChange}
              />
            </AccordionDetails>
          </Accordion>

          {/* Y Axis Settings */}
          <Accordion
            sx={{
              bgcolor: theme.palette.ui.panelMedium,
              color: "text.primary",
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="bold">
                {t("datasets:label.yAxis", "Y Axis")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <YAxisForm
                data={data}
                layout={layout}
                handleAxisChange={handleAxisChange}
                handleTraceChange={handleTraceChange}
              />
            </AccordionDetails>
          </Accordion>
        </>
      )}

      {/* Legend Settings */}
      <Accordion
        sx={{ bgcolor: theme.palette.ui.panelMedium, color: "text.primary" }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1" fontWeight="bold">
            {t("datasets:label.legend", "Legend")}
          </Typography>
        </AccordionSummary>
        <AccordionDetails
          sx={{ display: "flex", flexDirection: "column", gap: 2 }}
        >
          <LegendForm layout={layout} handleChange={handleChange} />
        </AccordionDetails>
      </Accordion>

      <Divider sx={{ my: 2, borderColor: theme.palette.ui.borderLight }} />

      <Stack direction="row" spacing={2} justifyContent="flex-end">
        <Button variant="outlined" onClick={handleCancel} disabled={!modified}>
          {t("common:cancel")}
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSave}
          disabled={!modified}
        >
          {t("common:save")}
        </Button>
      </Stack>
    </Box>
  );
}
