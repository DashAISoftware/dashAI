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
import { SaveDatasetModal } from "./SaveDatasetModal";
import { getConvertersByNotebookId } from "../../api/notebook";
import { getDatasetFile } from "../../api/datasets";
import DatasetTable from "./DatasetTable";
import { NotebookHistoryModal } from "./NotebookHistoryModal";

export default function DatasetPreviewNotebook({
  notebook,
  handleAddDatasetFromNotebook,
}) {
  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(notebook.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [notebook.file_path],
  );

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

  useEffect(() => {
    const fetchConverters = async () => {
      const response = await getConvertersByNotebookId(notebook.id);
      setConverters(response);
    };

    try {
      fetchConverters();
    } catch (error) {
      console.error("Error fetching converters:", error);
    }
  }, [notebook]);

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
                bgcolor: "#00BEBB",
                "&:hover": { bgcolor: "#008582" },
                "&:disabled": { bgcolor: "#444", color: "#666" },
                color: "white",
                fontWeight: "bold",
                fontSize: "0.7rem",
                px: 1.5,
                py: 0.5,
                textTransform: "uppercase",
                minWidth: "auto",
              }}
            >
              SAVE NEW DATA
            </Button>
            <IconButton
              size="small"
              sx={{ color: "#00BEBB", ml: 1 }}
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
          <Box>
            {" "}
            {/* Table */}
            <DatasetTable
              fetchPage={fetchDatasetPage}
              deps={[notebook.file_path]}
              initialPageSize={5}
              density="compact"
            />{" "}
          </Box>
        </AccordionDetails>
      </Accordion>
      <SaveDatasetModal
        open={showSaveDatasetModal}
        onClose={() => setShowSaveDatasetModal(false)}
        onSaveDataset={handleAddDatasetFromNotebook}
        appliedConverters={converters}
      />
      <NotebookHistoryModal
        open={showNotebookHistoryModal}
        onClose={() => setShowNotebookHistoryModal(false)}
        notebook={notebook}
      />
    </Box>
  );
}
