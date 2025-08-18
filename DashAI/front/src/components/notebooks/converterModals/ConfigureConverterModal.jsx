import React, { useState, useCallback } from "react";
import { Box, Typography, Dialog, IconButton, Tab, Tabs } from "@mui/material";
import DatasetSummaryTable from "../DatasetSummaryTable";
import { Close } from "@mui/icons-material";
import { getDatasetFile } from "../../../api/datasets";
import DatasetTable from "../DatasetTable";
import SummarizeIcon from "@mui/icons-material/Summarize";
import DatasetIcon from "@mui/icons-material/Dataset";
import { saveConverterList } from "../../../api/converter";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useFormik } from "formik";
import FormSchemaRenderFields from "../../shared/FormSchemaRenderFields";

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
      scope: {
        columns: [],
        rows: [],
      },
      order: 1,
      target_index: null,
    },
    // validationSchema,
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
          width: { xs: "90%", sm: "900px" },
          maxWidth: "100%",
        },
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center", // centers vertically
          height: "100%",
          width: "100%",
        }}
      >
        <Box
          sx={{
            p: 2,
            borderBottom: "1px solid #222",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6">
            Configure your converter: {converter.name}
          </Typography>
          <IconButton onClick={() => setOpen(false)}>
            <Close />
          </IconButton>
        </Box>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          centered
        >
          <Tab
            label={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <SummarizeIcon sx={{ fontSize: 18 }} />
                Summary
              </Box>
            }
          />
          <Tab
            label={
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <DatasetIcon sx={{ fontSize: 18 }} />
                Dataset
              </Box>
            }
          />
        </Tabs>
        <Box
          sx={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {activeTab === 0 && (
            <DatasetSummaryTable
              file={notebook.file_path}
              density="compact"
              hideFooter={true}
              disableColumnMenu={true}
              disableColumnFilter={true}
              disableColumnSelector={true}
              disableDensitySelector={true}
              sx={{ width: "100%" }}
            />
          )}
          <Box sx={{ display: activeTab === 1 ? "block" : "none" }}>
            <DatasetTable
              fetchPage={fetchDatasetPage}
              deps={[notebook.file_path]}
              initialPageSize={5}
              density="compact"
              disableColumnMenu={true}
              disableColumnFilter={true}
              disableColumnSelector={true}
              disableDensitySelector={true}
            />
          </Box>
        </Box>
        <Box sx={{ p: 2, flexShrink: 0 }}>
          <Typography variant="body2" color="text.secondary">
            Configure the settings for your dataset conversion.
          </Typography>
          <Box>
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
              setError={(error) => {
                console.error("Form error:", error);
              }}
              errorsMessage={formik.errors}
            />
          </Box>
        </Box>
      </Box>
    </Dialog>
  );
}
