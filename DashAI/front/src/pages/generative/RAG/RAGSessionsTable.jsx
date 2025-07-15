import React, { useState } from "react";
import PropTypes from "prop-types";

import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
  DeleteOutline as DeleteIcon,
  Visibility as ViewDocsIcon
} from "@mui/icons-material";
import { DataGrid } from "@mui/x-data-grid";
import {
  Button,
  Grid,
  Paper,
  Typography,
  LinearProgress,
} from "@mui/material";

import { deleteRAGSession } from "../../../api/rag";


export default function RAGSessionsTable({
  sessions,
  onSelect,
  onEdit,
  onOpenNewSessionModal
}) {

  const columns = [
    {
      field: "name",
      headerName: "Session Name",
      flex: 1,
      renderCell: (params) => (
        <Button
          size="small"
          onClick={() => onSelect(params.row.id, params.row.task_name)}
          sx={{ 
            textTransform: 'none', 
            justifyContent: 'flex-start', 
            padding: 0,
            color: 'white',
          }}
        >
          {params.value}
        </Button>
      )
    },
    {
      field: "created",
      headerName: "Created At",
      flex: 0.8,
      valueFormatter: (params) => new Date(params.value).toLocaleString()
    },
    {
      field: "",
      headerName: "Documents",
      flex: 0.6,
      valueGetter: (params) => params.row.parameters.documents.length
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1.1,
      renderCell: (params) => (
        <div>
          <Button
            size="small"
            variant="outlined"
            onClick={() => onSelect(params.row.id, params.row.task_name)}
            sx={{ mr: 1 }}
          >
            Open
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="secondary"
            onClick={() => onEdit(params.row)}
            sx={{ mr: 1 }}
            startIcon={<UpdateIcon />}
          >
            Edit
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
            startIcon={<DeleteIcon />}
          >
            Delete
          </Button>
        </div>
      )
    }
  ];

  return (
    <Paper sx={{ py: 4, px: 6 }}>
      <Grid container justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
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
          '& .MuiDataGrid-cell:focus': { outline: 'none' },
          minHeight: 400
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
    })
  ).isRequired,
  onSelect: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onOpenNewSessionModal: PropTypes.func.isRequired,
};
