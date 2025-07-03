import React, { useState } from "react";
import PropTypes from "prop-types";

import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
  DeleteOutline as DeleteIcon,
  Visibility as ViewDocsIcon
} from "@mui/icons-material";
import { DataGrid } from "@mui/x-data-grid"; // Removed GridToolbar as it's not strictly essential for basic rendering
import {
  Button,
  Grid,
  Paper,
  Typography,
  LinearProgress,
} from "@mui/material";

import { deleteRAGSession } from "../../../api/rag"; // Assuming this API call is correct

// Removed ConfirmDialog component as requested.
// Removed useSnackbar import and usage.

export default function RAGSessionsTable({
  sessions,
  onSelect,
  onEdit,
  // Removed onRefreshSessions prop as it's not needed in this simplified version
  onOpenNewSessionModal
}) {
  // Removed local 'loading' state for operations within the table,
  // as the parent RAGHomePage handles the main loading.
  // Removed showConfirmDelete and sessionToDelete states.


  // Removed handleDeleteSession function as its logic involved removed features.
  // The delete button will now just call the API directly (or a simplified parent handler).

  const columns = [
    {
      field: "name",
      headerName: "Session Name",
      flex: 1,
      renderCell: (params) => (
        <Button
          size="small"
          onClick={() => onSelect(params.row.id, params.row.task_name)}
          sx={{ textTransform: 'none', justifyContent: 'flex-start', padding: 0 }}
        >
          {params.value}
        </Button>
      )
    },
    {
      field: "created_at",
      headerName: "Created At",
      flex: 1,
      valueFormatter: (params) => new Date(params.value).toLocaleString()
    },
    {
      field: "documents",
      headerName: "Documents",
      flex: 0.7,
      valueGetter: (params) => params.row.documents?.length || 0
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 1.5,
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
          {/* Simplified Delete button: It will now rely on a parent handler or direct API call */}
          <Button
            size="small"
            variant="outlined"
            color="error"
            onClick={async () => {
              // Directly call the delete API. No confirmation dialog.
              try {
                // Assuming deleteRAGSession is imported and handles the actual deletion
                await deleteRAGSession(params.row.id);
                // If the parent component (RAGHomePage) needs to refresh, it will do so
                // based on its own state updates or a prop passed down for that purpose.
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
        // 'loading' prop here should ideally come from the parent (RAGHomePage)
        // For this simplified version, we'll assume the parent manages it.
        // If the table appears empty or stuck, check RAGHomePage's 'loading' state.
        loading={false} // Set to false to ensure it's not stuck in loading from this component
        slots={{
          loadingOverlay: LinearProgress,
        }}
        getRowId={(row) => row.id}
        sx={{
          '& .MuiDataGrid-cell:focus': { outline: 'none' },
          minHeight: 400
        }}
      />

      {/* Removed ConfirmDialog component */}
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
  // Removed onRefreshSessions from propTypes
  onOpenNewSessionModal: PropTypes.func.isRequired,
};
