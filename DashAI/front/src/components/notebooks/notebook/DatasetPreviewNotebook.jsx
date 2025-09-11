import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Typography,
  Button,
  IconButton,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { Add } from "@mui/icons-material";
import HistoryIcon from "@mui/icons-material/History";
import { SaveDatasetModal } from "../datasetCreation/SaveDatasetModal";
import { getConvertersByNotebookId } from "../../../api/notebook";
import { getDatasetFile } from "../../../api/datasets";
import DatasetTable from "../dataset/DatasetTable";
import { NotebookHistoryModal } from "./NotebookHistoryModal";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";

export default function DatasetPreviewNotebook({
  notebook,
  handleAddDatasetFromNotebook,
}) {
  if (!notebook) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <CircularProgress sx={{ color: "#00BEBB" }} />
        <Typography>Loading...</Typography>
      </Box>
    );
  }
  const [showSaveDatasetModal, setShowSaveDatasetModal] = useState(false);
  const [showNotebookHistoryModal, setShowNotebookHistoryModal] =
    useState(false);
  const [converters, setConverters] = useState([]);
  const { explorersAndConverters } = useExplorersAndConverters();

  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(notebook.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [notebook, converters],
  );

  useEffect(() => {
    let intervalId;

    const fetchConverters = async () => {
      try {
        const response = await getConvertersByNotebookId(notebook.id);
        setConverters(response);

        // Check if any converters are in a pending state (status < 3)
        const isPollingNeeded = response.some(
          (converter) => converter.status < 3,
        );

        if (isPollingNeeded) {
          // If polling is needed, start the interval
          if (!intervalId) {
            intervalId = setInterval(fetchConverters, 2000); // Poll every 2 seconds
          }
        } else {
          // If all converters are in a final state, clear the interval
          clearInterval(intervalId);
        }
      } catch (error) {
        console.error("Error fetching converters:", error);
        clearInterval(intervalId); // Clear interval on error
      }
    };

    fetchConverters();

    // Cleanup function to clear the interval when the component unmounts
    // or when the dependencies change
    return () => {
      clearInterval(intervalId);
    };
  }, [notebook, explorersAndConverters]);

  return (
    <Box
      sx={{
        mb: 2,
      }}
    >
      <Accordion
        width="100%"
        sx={{ bgcolor: "#212121", borderRadius: 2, boxShadow: "none" }}
        defaultExpanded={true}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon sx={{ color: "white" }} />}
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            "& .MuiAccordionSummary-content": {
              flexGrow: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              margin: "0px 0 !important",
            },
          }}
        >
          <Typography variant="h6">Dataset Preview</Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {/* Save Dataset Button */}
            <Button
              variant="contained"
              size="small"
              endIcon={<Add />}
              onClick={(e) => {
                e.stopPropagation();
                setShowSaveDatasetModal(true);
              }}
              disabled={false}
              sx={{
                fontSize: "0.7rem",
                px: 1.5,
                py: 0.5,
                textTransform: "uppercase",
                minWidth: "auto",
              }}
            >
              Save as new Dataset
            </Button>
            <IconButton
              size="small"
              sx={{ color: "primary.main", ml: 1 }}
              onClick={(e) => {
                e.stopPropagation();
                setShowNotebookHistoryModal(true);
              }}
            >
              <HistoryIcon />
            </IconButton>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ height: 345, width: "100%" }}>
            {" "}
            {/* Table */}
            <DatasetTable
              fetchPage={fetchDatasetPage}
              deps={[notebook.file_path]}
              initialPageSize={5}
              density="compact"
              datasetPath={notebook.file_path}
              initialState={{
                pagination: {
                  paginationModel: {
                    pageSize: 5,
                  },
                },
              }}
              pageSizeOptions={[5]}
              autoHeight={false}
              disableDensitySelector
              componentsProps={{
                noRowsOverlay: {
                  style: { height: "100%" },
                },
              }}
              sx={{
                height: "100%",
                "& .MuiDataGrid-virtualScroller": {
                  "overflow-y": "hidden",
                },
                "& .MuiDataGrid-overlay": {
                  height: "100%",
                },
              }}
            />{" "}
          </Box>
        </AccordionDetails>
      </Accordion>
      <SaveDatasetModal
        open={showSaveDatasetModal}
        onClose={() => setShowSaveDatasetModal(false)}
        onSaveDataset={handleAddDatasetFromNotebook}
        appliedConverters={converters.filter(
          (converter) => converter.status === 3,
        )} // Only show finished converters
      />
      <NotebookHistoryModal
        open={showNotebookHistoryModal}
        onClose={() => setShowNotebookHistoryModal(false)}
        notebook={notebook}
        converters={converters.filter((converter) => converter.status === 3)} // Only show finished converters
      />
    </Box>
  );
}
