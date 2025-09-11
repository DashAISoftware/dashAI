import React, { useState, useCallback } from "react";
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
} from "@mui/material";
import { Close } from "@mui/icons-material";
import DatasetIcon from "@mui/icons-material/Dataset";

import DatasetTable from "./dataset/DatasetTable";
import DescriptionIcon from "@mui/icons-material/Description";

import { getDatasetFile } from "../../api/datasets";

export default function ConfigureToolModal({
  tool,
  open,
  handleClose,
  notebook,
  FormSection,
}) {
  if (!tool) return null;

  const [activeTab, setActiveTab] = useState(0);
  const [step, setStep] = useState(0);

  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(notebook.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [notebook.file_path],
  );

  const steps = ["Configure Scope", "Configure Parameters"];

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      PaperProps={{
        sx: {
          width: { xs: "95%", sm: "1200px" },
          maxWidth: "100%",
          borderRadius: 2,
          height: "90vh", // fixed modal height
          display: "flex",
          flexDirection: "column",
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
          Configure {tool.type}: {tool.name}
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
          label="Description"
        />
        <Tab
          icon={<DatasetIcon fontSize="small" />}
          iconPosition="start"
          label="Dataset"
        />
      </Tabs>

      {/* CONTENT AREA */}
      <Box
        sx={{
          flex: 1,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Tab Panels */}
        <Box sx={{ flex: 1, overflow: "auto", p: 2, height: "35%" }}>
          {activeTab === 0 && (
            <Typography
              variant="body2"
              color="text.secondary"
              gutterBottom
              //textAlign="center"
            >
              {tool.description || "No description available."}
            </Typography>
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
            />
          )}
        </Box>

        {/* FORM at the bottom */}
        <Box
          sx={{
            p: 2,
            borderTop: "1px solid",
            borderColor: "divider",
            height: "65%",
            overflow: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Typography
            variant="body2"
            color="text.secondary"
            gutterBottom
            textAlign="center"
          >
            Configure the settings
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
