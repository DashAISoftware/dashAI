import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  Box,
  Typography,
  Dialog,
  IconButton,
  Tab,
  Tabs,
  Stepper,
  Step,
  StepLabel,
  Tooltip,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { Close, UnfoldMore } from "@mui/icons-material";
import DatasetIcon from "@mui/icons-material/Dataset";

import DatasetTable from "../dataset/DatasetTable";
import DescriptionIcon from "@mui/icons-material/Description";
import api from "../../../api/api";

import { getDatasetFile } from "../../../api/datasets";
import { useTranslation } from "react-i18next";

export default function ConfigureToolModal({
  tool,
  open,
  handleClose,
  notebook,
  FormSection,
}) {
  const theme = useTheme();
  if (!tool) return null;

  const [activeTab, setActiveTab] = useState(0);
  const [step, setStep] = useState(0);
  const containerRef = useRef(null);
  const [topHeight, setTopHeight] = useState(100);
  const isResizingRef = useRef(false);
  const { t } = useTranslation(["datasets", "common"]);

  const handleMouseDown = () => {
    isResizingRef.current = true;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
  };

  const handleMouseMove = (e) => {
    if (!isResizingRef.current || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const offsetY = e.clientY - rect.top;

    // Limit min/max
    const minHeight = 0;
    const maxHeight = rect.height - 150;
    const newHeight = Math.max(minHeight, Math.min(maxHeight, offsetY));

    setTopHeight(newHeight);
  };

  const handleMouseUp = () => {
    isResizingRef.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  };

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(notebook.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [notebook.file_path],
  );

  const steps =
    Object.values(tool.schema.properties).length > 0
      ? [
          t("datasets:label.configureScope"),
          t("datasets:label.configureParameters"),
        ]
      : [t("datasets:label.configureScope")];

  return (
    <Dialog
      open={open}
      onClose={() => {}}
      slotProps={{
        paper: {
          sx: {
            width: { xs: "95%", sm: "1200px" },
            maxWidth: "100%",
            borderRadius: 2,
            height: "90vh",
            display: "flex",
            flexDirection: "column",
          },
        },
      }}
    >
      {/* HEADER */}
      <Box
        sx={{
          p: 2,
          borderBottom: "1px solid",
          borderColor: "divider",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <Typography variant="h6" fontWeight="600" sx={{ whiteSpace: "nowrap" }}>
          {t("datasets:label.configureToolTitle", {
            toolType: tool.type,
            toolName: tool.display_name,
          })}
        </Typography>

        {/* Stepper */}
        <Box sx={{ flex: 1 }}>
          <Stepper activeStep={step}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        <IconButton onClick={handleClose}>
          <Close />
        </IconButton>
      </Box>
      {/* TABS */}
      <Tabs
        value={activeTab}
        onChange={(_, newValue) => setActiveTab(newValue)}
        centered
        sx={{
          minHeight: "36px",
          "& .MuiTab-root": {
            minHeight: "36px",
            fontSize: "0.85rem",
          },
          "& .MuiTabs-indicator": {
            height: "2px",
          },
        }}
      >
        <Tab
          icon={<DescriptionIcon fontSize="small" />}
          iconPosition="start"
          label={t("common:description")}
        />
        <Tab
          icon={<DatasetIcon fontSize="small" />}
          iconPosition="start"
          label={t("common:dataset")}
        />
      </Tabs>
      {/* CONTENT AREA */}
      <Box
        ref={containerRef}
        sx={{
          flex: 1,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          position: "relative",
        }}
      >
        {/* Tab Panels */}
        <Box
          sx={{
            height: `${topHeight}px`,
            overflow: "auto",
            p: 2,
            flexShrink: 0,
          }}
        >
          {activeTab === 0 && (
            <>
              {/* Tool Description */}
              <Box
                sx={{
                  bgcolor: "theme.palette.background.box",
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 1.5,
                  p: 2,
                }}
              >
                <Typography
                  variant="subtitle2"
                  sx={{
                    mb: 1,
                    display: "block",
                  }}
                >
                  {t("common:description")}
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    color: "text.secondary",
                    lineHeight: 1.6,
                    mb: 2,
                  }}
                >
                  {tool.description || t("common:noDescription")}
                </Typography>
                <img
                  src={`${api.defaults.baseURL}/v1/component/image/${tool.name}`}
                  alt={tool.display_name}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    display: "block",
                  }}
                />
              </Box>
            </>
          )}
          {activeTab === 1 && (
            <DatasetTable
              fetchPage={fetchDatasetPage}
              deps={[notebook.file_path]}
              initialPageSize={5}
              density="compact"
              disableColumnMenu
              disableColumnFilter
              disableColumnSelector
              disableDensitySelector
              datasetPath={notebook.file_path}
              containerHeight={topHeight - 48}
              autoHeight={false}
              slots={{ toolbar: null }}
            />
          )}
        </Box>

        {/* Divider for resizing */}
        <Tooltip title={t("datasets:label.dragToResize")} placement="top" arrow>
          <Box
            onMouseDown={handleMouseDown}
            sx={{
              height: "24px",
              cursor: "row-resize",
              backgroundColor: "divider",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
              transition: "all 0.2s",
              "&:hover": {
                backgroundColor: theme.palette.primary.main,
                "& .drag-icon": {
                  color: "white",
                },
              },
              zIndex: 2,
            }}
          >
            <UnfoldMore
              className="drag-icon"
              sx={{
                fontSize: 22,
                color: "text.secondary",
                transition: "color 0.2s",
              }}
            />
          </Box>
        </Tooltip>

        {/* Bottom section (form) */}
        <Box
          sx={{
            flex: 1,
            overflow: "auto",
            p: 2,
            borderTop: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography
            variant="body2"
            color="text.secondary"
            gutterBottom
            textAlign="center"
          >
            {t("common:configureTheSettings")}
          </Typography>
          <FormSection
            step={step}
            setStep={setStep}
            handleClose={handleClose}
            tool={tool}
            notebook={notebook}
          />
        </Box>
      </Box>
    </Dialog>
  );
}
