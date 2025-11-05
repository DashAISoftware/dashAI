import React, { useState } from "react";
import PropTypes from "prop-types";

import AddIcon from "@mui/icons-material/AddCircleOutline";
import EditIcon from "@mui/icons-material/Edit";
import VisibilityIcon from "@mui/icons-material/Visibility";

import { DataGrid } from "@mui/x-data-grid";
import {
  Button,
  Grid,
  Paper,
  Typography,
  LinearProgress,
  IconButton,
  Tooltip,
} from "@mui/material";
import DeleteItemModal from "../../../components/custom/DeleteItemModal";

import { deleteRAGSession } from "../../../api/rag";
import { formatDate } from "../../../utils";

export default function RAGSessionsTable({
  sessions,
  onSelect,
  onEdit,
  onOpenNewSessionModal,
  onRemove,
  showTableTitle = false,
}) {
  const columns = React.useMemo(
    () => [
      {
        field: "name",
        headerName: "Session Name",
        flex: 0.6,
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
        field: "last_modified",
        headerName: "Last Modified",
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
        type: "actions",
        headerName: "Actions",
        minWidth: 100,
        flex: 0.5,
        getActions: (params) => [
          <Tooltip title="Open" key="open">
            <IconButton
              size="small"
              sx={{ color: "white" }}
              onClick={() => onSelect(params.row.id, params.row.task_name)}
            >
              <VisibilityIcon fontSize="small" />
            </IconButton>
          </Tooltip>,
          <Tooltip title="Edit" key="edit">
            <IconButton
              size="small"
              sx={{ color: "white" }}
              onClick={() => onEdit(params.row)}
            >
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>,
          <DeleteItemModal
            key="delete-button"
            deleteFromTable={async () => {
              try {
                await deleteRAGSession(params.row.id);
                if (onRemove) onRemove(params.row.id);
              } catch (error) {
                console.error("Error deleting session:", error);
              }
            }}
            item="session"
          />,
        ],
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
            Current RAG sessions
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
      created_at: PropTypes.string,
      documents: PropTypes.array,
      task_name: PropTypes.string,
    }),
  ).isRequired,
  onSelect: PropTypes.func.isRequired,
  onEdit: PropTypes.func.isRequired,
  onOpenNewSessionModal: PropTypes.func.isRequired,
  onRemove: PropTypes.func,
};
