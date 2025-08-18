import React, { useState, useCallback } from "react";
import {
  Box,
  Typography,
  Dialog,
  IconButton,
  Tab,
  Tabs,
  Divider,
  Paper,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import SummarizeIcon from "@mui/icons-material/Summarize";
import DatasetIcon from "@mui/icons-material/Dataset";
import { useFormik } from "formik";

import DatasetSummaryTable from "../DatasetSummaryTable";
import DatasetTable from "../DatasetTable";
import FormSchemaRenderFields from "../../shared/FormSchemaRenderFields";
import { getDatasetFile } from "../../../api/datasets";
import { saveConverterList } from "../../../api/converter";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";

export default function ConfigureConverterModal({
  open,
  setOpen,
  converter,
  notebook,
}) {
  if (!converter) return null;

  const [activeTab, setActiveTab] = useState(0);
  const { explorersAndConverters, setExplorersAndConverters } =
    useExplorersAndConverters();

  const formik = useFormik({
    initialValues: {
      params: { ...converter.schema.properties },
      scope: { columns: [], rows: [] },
      order: 1,
      target_index: null,
    },
    enableReinitialize: true,
    onSubmit: async (values) => {
      try {
        saveConverterList(values).then((converter) => {
          enqueueConverterJob(converter.id).then(() => {
            const converterToAdd = { ...converter, type: "converter" };
            setExplorersAndConverters([
              ...explorersAndConverters,
              converterToAdd,
            ]);
          });
        });
      } catch (error) {
        console.error("Error creating Converter:", error);
      }
    },
  });

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
      onClose={() => setOpen(false)}
      PaperProps={{
        sx: {
          width: { xs: "95%", sm: "1200px" },
          maxWidth: "100%",
          borderRadius: 3,
          height: "85vh", // fixed modal height
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
          minHeight: "36px", // reduce overall tab height
          "& .MuiTab-root": {
            minHeight: "36px",
            fontSize: "0.85rem",
          },
          "& .MuiTabs-indicator": {
            height: "2px", // thinner indicator
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

      {/* CONTENT AREA with fixed height + scroll */}
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
              sx={{ minHeight: "100%" }}
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
              sx={{ minHeight: "100%" }}
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
          }}
        >
          <Typography
            variant="body2"
            color="text.secondary"
            gutterBottom
            textAlign="center"
          >
            Configure the settings for your dataset conversion
          </Typography>

          <FormSchemaRenderFields
            modelSchema={converter.schema.properties}
            formik={formik}
            autoSave={false}
            handleUpdateSchema={(updatedValues) => {
              formik.setValues((prevValues) => ({
                ...prevValues,
                ...updatedValues,
              }));
            }}
            onFormSubmit={formik.handleSubmit}
            setError={(error) => console.error("Form error:", error)}
            errorsMessage={formik.errors}
          />
        </Box>
      </Box>
    </Dialog>
  );
}
