import React, { useState, useCallback } from "react";
import { Box, Typography, Dialog, IconButton, Tab, Tabs } from "@mui/material";
import { Close } from "@mui/icons-material";
import SummarizeIcon from "@mui/icons-material/Summarize";
import DatasetIcon from "@mui/icons-material/Dataset";

import DatasetSummaryTable from "../DatasetSummaryTable";
import DatasetTable from "../DatasetTable";
import { getDatasetFile } from "../../../api/datasets";
import FormSection from "./FormSection";

export default function ConfigureConverterModal({
  open,
  handleClose,
  converter,
  notebook,
}) {
  if (!converter) return null;

  const [activeTab, setActiveTab] = useState(0);

  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(notebook.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [notebook.file_path],
  );

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      PaperProps={{
        sx: {
          width: { xs: "95%", sm: "1200px" },
          maxWidth: "100%",
          borderRadius: 3,
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
        }}
      >
        <Typography variant="h6" fontWeight="600">
          Configure Converter: {converter.name}
        </Typography>
        <IconButton onClick={() => setOpen(false)}>
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
          icon={<SummarizeIcon fontSize="small" />}
          iconPosition="start"
          label="Summary"
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
            <DatasetSummaryTable
              file={notebook.file_path}
              density="compact"
              hideFooter
              disableColumnMenu
              disableColumnFilter
              disableColumnSelector
              disableDensitySelector
            />
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
            />
          )}
        </Box>

        {/* FORM at the bottom */}
        <FormSection
          converter={converter}
          notebook={notebook}
          handleSubmit={() => {
            handleClose();
          }}
        />
      </Box>
    </Dialog>
  );
}
