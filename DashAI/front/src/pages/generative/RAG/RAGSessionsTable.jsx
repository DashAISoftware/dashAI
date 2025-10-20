import React, { useState } from "react";
import PropTypes from "prop-types";

import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
  Edit as EditIcon,
  DeleteOutline as DeleteIcon,
  Visibility as ViewDocsIcon,
} from "@mui/icons-material";

import { DataGrid } from "@mui/x-data-grid";
import { Button, Grid, Paper, Typography, LinearProgress } from "@mui/material";

import { deleteRAGSession } from "../../../api/rag";
import { formatDate } from "../../../utils";

export default function RAGSessionsTable({
  sessions,
  onSelect,
  onEdit,
  onOpenNewSessionModal,
  showTableTitle = false,
}) {
  const columns = React.useMemo(
    () => [
      {
        field: "name",
        headerName: "Session Name",
        flex: 0.8,
        renderCell: (params) => (
          <Button
            size="small"
            onClick={() => onSelect(params.row.id, params.row.task_name)}
            sx={{
              textTransform: "none",
              justifyContent: "flex-start",
              padding: 0,
              color: "white",
            }}
          >
            {params.value}
          </Button>
        ),
      },
      {
        field: "created",
        headerName: "Created At",
        flex: 0.4,
        valueGetter: (value) => {
          if (!value) return "";
          return formatDate(value);
        },
      },
      {
        field: "documents",
        headerName: "Documents",
        flex: 0.4,
        valueGetter: (value, row) => {
          if (!row || !row.parameters || !row.parameters.documents) {
            return 0;
          }
          return row.parameters.documents.length || 0;
        },
      },
      {
        field: "actions",
        headerName: "Actions",
        flex: 0.9,
        renderCell: (params) => (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              width: "100%",
              gap: "auto",
            }}
          >
            <Button
              size="small"
              variant="outlined"
              onClick={() => onSelect(params.row.id, params.row.task_name)}
            >
              Open
            </Button>
            <Button
              size="small"
              variant="outlined"
              color="warning"
              onClick={() => onEdit(params.row)}
            >
              <EditIcon />
            </Button>
            <Button
              size="small"
              variant="outlined"
              color="error"
              onClick={async () => {
                try {
                  await deleteRAGSession(params.row.id);
                } catch (error) {
                  console.error("Error deleting session:", error);
                }
              }}
            >
              <DeleteIcon />
            </Button>
          </div>
        ),
      },
    ],
    [onSelect, onEdit],
  );

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
            RAG Sessions
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={onOpenNewSessionModal}
            startIcon={<AddIcon />}
          >
            New RAG Session
          </Button>
        </Grid>
      )}
      {!showTableTitle && (
        <Grid
          container
          justifyContent="flex-end"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Button
            variant="contained"
            color="primary"
            onClick={onOpenNewSessionModal}
            startIcon={<AddIcon />}
          >
            New RAG Session
          </Button>
        </Grid>
      )}
      <DataGrid
        rows={sessions}
        columns={columns}
        initialState={{
          pagination: { paginationModel: { pageSize: 5 } },
        }}
        pageSizeOptions={[5, 10]}
        disableRowSelectionOnClick
        autoHeight
        loading={false}
        slots={{
          loadingOverlay: LinearProgress,
        }}
        getRowId={(row) => row.id}
        sx={{
          "& .MuiDataGrid-cell:focus": { outline: "none" },
          minHeight: 300,
        }}
      />
    </Paper>
  );
}

RAGSessionsTable.propTypes = {
  sessions: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      created_at: PropTypes.string.isRequired,
      documents: PropTypes.array,
      task_name: PropTypes.string,
    }),
  ).isRequired,
  onSelect: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onOpenNewSessionModal: PropTypes.func.isRequired,
};
