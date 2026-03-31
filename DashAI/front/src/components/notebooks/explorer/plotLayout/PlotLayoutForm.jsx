import React, { useState, useCallback, memo } from "react";
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
import { useTheme } from "@mui/material/styles";

import GeneralForm from "./forms/GeneralForm";
import TraceForm from "./forms/TraceForm";
import XAxisForm from "./forms/XAxisForm";
import YAxisForm from "./forms/YAxisForm";
import LegendForm from "./forms/LegendForm";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DimensionsForm from "./forms/DimensionsForm";
import { useTranslation } from "react-i18next";

const PlotLayoutForm = memo(function PlotLayoutForm({
  data,
  setData,
  layout,
  setLayout,
  onSave,
  sx = {},
}) {
  const theme = useTheme();
  const { t } = useTranslation(["datasets", "common"]);
  const [modified, setModified] = useState(false);
  const [localLayout, setLocalLayout] = useState(() => structuredClone(layout));
  const [localData, setLocalData] = useState(() => structuredClone(data));

  const handleTraceChange = useCallback(
    (index, path, value) => {
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
    },
    [data, setData],
  );

  const handleChange = useCallback(
    (field, value) => {
      setLayout({ ...layout, [field]: value });
      setModified(true);
    },
    [layout, setLayout],
  );

  const handleCancel = useCallback(() => {
    setLayout(structuredClone(localLayout));
    setData(structuredClone(localData));
    setModified(false);
  }, [localLayout, localData, setLayout, setData]);

  const handleSave = useCallback(() => {
    setLocalData(structuredClone(data));
    setLocalLayout(structuredClone(layout));
    setModified(false);
    onSave();
  }, [data, layout, onSave]);

  const handleAxisChange = useCallback(
    (axis, field, value) => {
      setLayout({
        ...layout,
        [axis]: { ...layout[axis], [field]: value },
      });
      setModified(true);
    },
    [layout, setLayout],
  );

  const accordionSx = {
    bgcolor: theme.palette.ui.panelMedium,
    color: "text.primary",
  };

  if (!layout) return null;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 2,
        width: "100%",
        height: "100%",
        bgcolor: theme.palette.background.box,
        color: "text.primary",
        p: 2,
        ...sx,
      }}
    >
      <Typography variant="h6" sx={{ mb: 1 }}>
        {t("datasets:label.editPlotLayout")}
      </Typography>

      <Divider />

      <Box
        sx={{
          overflowY: "auto",
          height: "100%",
        }}
      >
        {/* General Settings */}
        <Accordion defaultExpanded sx={accordionSx}>
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
            <Accordion key={trace.name || trace.type || `trace-${index}`} sx={accordionSx}>
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
          <Accordion sx={accordionSx}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="bold">
                {t("datasets:label.dimensionsLabels")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              <DimensionsForm
                data={data}
                handleTraceChange={handleTraceChange}
              />
            </AccordionDetails>
          </Accordion>
        ) : (
          <>
            {/* X Axis Settings */}
            <Accordion sx={accordionSx}>
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
            <Accordion sx={accordionSx}>
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
        <Accordion sx={accordionSx}>
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
      </Box>

      <Divider sx={{ mt: 1, borderColor: theme.palette.ui.borderLight }} />

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
});

export default PlotLayoutForm;
