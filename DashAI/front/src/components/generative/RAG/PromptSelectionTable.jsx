import React, { useState } from "react";
import { Box, Paper, Tooltip, IconButton } from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { DataGrid } from "@mui/x-data-grid";
import { formatDate } from "../../../utils";
import TemplateModal from "../../custom/TemplateModal";

export default function PromptSelectionTable({ prompts = [] }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState("");

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

  return (
    <Paper sx={{ py: 2, px: 3 }}>
      <Box sx={{ height: 400, width: "100%" }}>
        <DataGrid
          rows={prompts}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 5,
              },
            },
          }}
          pageSizeOptions={[5, 10, 25, 50]}
          disableRowSelectionOnClick
          autoHeight
        />
        <TemplateModal
          open={modalOpen}
          handleClose={handleCloseModal}
          template={selectedTemplate}
        />
      </Box>
    </Paper>
  );
}
