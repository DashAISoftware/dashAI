import React, { useState } from "react";
import {
  Paper,
  Typography,
  IconButton,
  Tooltip,
  LinearProgress,
} from "@mui/material";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { formatDate } from "../../../utils";
import DeleteItemModal from "../../custom/DeleteItemModal";
import DocumentPreviewModal from "./DocumentPreviewModal";

export default function DocumentTable({
  documents,
  onRemove,
  isLoading = false,
  tableTitle = null,
}) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [txtContent, setTxtContent] = useState("");

  const handleOpenPreview = async (doc) => {
    setPreviewDoc(doc);
    if (doc.file_type === "txt" && doc.preview) {
      try {
        const res = await fetch(doc.preview);
        const text = await res.text();
        setTxtContent(text);
      } catch (e) {
        setTxtContent("Error loading TXT file");
      }
    }
    setPreviewOpen(true);
  };

  const handleClosePreview = () => {
    setPreviewOpen(false);
    setPreviewDoc(null);
    setTxtContent("");
  };

  const columns = [
    { field: "id", headerName: "ID", minWidth: 50, flex: 0.5, editable: false },
    {
      field: "file_name",
      headerName: "Name",
      minWidth: 220,
      flex: 1,
      editable: false,
    },
    {
      field: "created",
      headerName: "Added On",
      minWidth: 140,
      flex: 0.5,
      editable: false,
      valueGetter: (value) => formatDate(value),
    },
    {
      field: "last_modified",
      headerName: "Last Modified",
      minWidth: 140,
      flex: 0.5,
      editable: false,
      valueGetter: (value, row) => {
        return row?.optional_metadata?.last_modified
          ? formatDate(row.optional_metadata.last_modified)
          : "N/A";
      },
    },
    {
      field: "actions",
      type: "actions",
      headerName: "Actions",
      minWidth: 100,
      flex: 0.3,
      getActions: (params) => [
        <Tooltip title="Preview" key="preview">
          <IconButton
            size="small"
            onClick={() => handleOpenPreview(params.row)}
          >
            <VisibilityIcon fontSize="small" />
          </IconButton>
        </Tooltip>,
        <DeleteItemModal
          key="delete-button"
          deleteFromTable={() => onRemove(params.row.id)}
          item="document"
        />,
      ],
    },
  ];

  return (
    <Paper sx={{ py: 4, px: 4 }}>
      {tableTitle && (
        <Typography variant="h6" component="h2" sx={{ mb: 2 }}>
          {tableTitle}
        </Typography>
      )}
      {documents.length === 0 && !isLoading ? (
        <Typography
          variant="body1"
          color="warning.main"
          textAlign="center"
          mt={16}
          mx={"auto "}
        >
          No documents available.
        </Typography>
      ) : (
        <DataGrid
          rows={documents}
          columns={columns}
          initialState={{
            pagination: { paginationModel: { pageSize: 5 } },
          }}
          pageSizeOptions={[5, 10]}
          disableRowSelectionOnClick
          autoHeight
          loading={isLoading}
          slots={{
            loadingOverlay: LinearProgress,
          }}
          getRowId={(row) => row.id}
          sx={{
            "& .MuiDataGrid-cell:focus": { outline: "none" },
            minHeight: 300,
          }}
        />
      )}
      <DocumentPreviewModal
        open={previewOpen}
        onClose={handleClosePreview}
        document={previewDoc}
        txtContent={txtContent}
      />
    </Paper>
  );
}

DocumentTable.propTypes = {
  documents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      createdAt: PropTypes.string.isRequired,
      preview: PropTypes.string,
    }),
  ).isRequired,
  onRemove: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
};
