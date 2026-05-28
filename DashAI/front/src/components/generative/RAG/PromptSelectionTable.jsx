import React, { useState } from "react";
import {
  Box,
  Paper,
  Tooltip,
  IconButton,
  Button,
  Grid,
  Typography,
} from "@mui/material";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { DataGrid } from "@mui/x-data-grid";
import { formatDate } from "../../../utils";
import TemplateModal from "../../custom/TemplateModal";
import NewPromptModal from "../../../pages/generative/simplified-RAG/advanced/NewPromptModal";
import { getRAGPrompts } from "../../../api/rag";

export default function PromptSelectionTable({
  prompts = [],
  loading = false,
  rowSelectionModel = [],
  onRowSelectionModelChange,
  showTableTitle = false,
  setSessionData,
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [newPromptModalOpen, setNewPromptModalOpen] = useState(false);
  const [promptRows, setPromptRows] = useState([]);
  React.useEffect(() => {
    async function fetchPrompts() {
      const initialPrompts = await getRAGPrompts();
      initialPrompts.sort((a, b) => new Date(b.created) - new Date(a.created));
      setPromptRows(initialPrompts);
    }
    fetchPrompts();
  }, []);

  const handleViewTemplate = (template) => {
    setSelectedTemplate(template);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedTemplate("");
  };

  const columns = React.useMemo(
    () => [
      {
        field: "id",
        headerName: "ID",
        minWidth: 50,
        flex: 0.3,
        editable: false,
      },
      {
        field: "name",
        headerName: "Name",
        minWidth: 140,
        flex: 1,
        editable: false,
      },
      {
        field: "class_name",
        headerName: "Type",
        minWidth: 140,
        flex: 1,
        editable: false,
      },
      {
        field: "language",
        headerName: "Language",
        minWidth: 100,
        flex: 0.7,
        editable: false,
        valueGetter: (value, row) => {
          const lang = row.parameters?.language;
          const langMap = { en: "English", es: "Español", pt: "Português" };
          if (lang) {
            return langMap[lang] || lang;
          }
          return row.class_name?.startsWith("Default") ? "English" : "-";
        },
      },
      {
        field: "created",
        headerName: "Created",
        minWidth: 140,
        flex: 1,
        editable: false,
        valueGetter: (value) => formatDate(value),
      },
      {
        field: "last_modified",
        headerName: "Edited",
        minWidth: 140,
        flex: 1,
        editable: false,
        valueGetter: (value) => formatDate(value),
      },
      {
        field: "actions",
        type: "actions",
        headerName: "Actions",
        minWidth: 80,
        flex: 0.4,
        getActions: (params) => [
          <Tooltip title="View prompt" key="preview">
            <IconButton
              size="small"
              onClick={() =>
                handleViewTemplate(params.row.parameters?.template || "")
              }
            >
              <VisibilityIcon fontSize="small" />
            </IconButton>
          </Tooltip>,
        ],
      },
    ],
    [],
  );

  const handlePromptCreated = async (newPromptId) => {
    const updatedPrompts = await getRAGPrompts();
    updatedPrompts.sort((a, b) => new Date(b.created) - new Date(a.created));
    setPromptRows(updatedPrompts);
    if (onRowSelectionModelChange && newPromptId) {
      onRowSelectionModelChange([newPromptId]);
    }
    if (setSessionData && newPromptId) {
      setSessionData((prev) => ({
        ...prev,
        parameters: {
          ...prev.parameters,
          prompt_id: newPromptId,
        },
      }));
    }
    setNewPromptModalOpen(false);
  };

  return (
    <Paper sx={{ py: 4, px: 4 }}>
      {showTableTitle && (
        <Grid
          container
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Typography variant="h5" component="h2">
            Current prompts
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={() => setNewPromptModalOpen(true)}
            startIcon={<AddIcon />}
          >
            New Prompt
          </Button>
        </Grid>
      )}
      {!showTableTitle && (
        <Grid
          container
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Typography variant="subtitle1" component="p" sx={{ mb: 2 }}>
            Choose or customize your prompt to define the model's behavior.
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={() => setNewPromptModalOpen(true)}
            startIcon={<AddIcon />}
          >
            New Prompt
          </Button>
        </Grid>
      )}
      <Box sx={{ height: "100%" }}>
        <DataGrid
          rows={promptRows}
          columns={columns}
          hideFooter
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 5,
              },
            },
          }}
          pageSizeOptions={[5, 10, 25, 50]}
          autoHeight
          loading={loading}
        />
        <TemplateModal
          open={modalOpen}
          handleClose={handleCloseModal}
          template={selectedTemplate}
        />
        <NewPromptModal
          open={newPromptModalOpen}
          handleClose={() => setNewPromptModalOpen(false)}
          onPromptCreated={handlePromptCreated}
          existingPrompts={promptRows}
        />
      </Box>
    </Paper>
  );
}
