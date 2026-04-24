import React, { useState } from "react";
import { Box, IconButton, Tooltip, LinearProgress } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import VisibilityIcon from "@mui/icons-material/Visibility";
import PropTypes from "prop-types";
import { formatDate } from "../../../utils";
import DeleteItemModal from "../../custom/DeleteItemModal";
import DocumentPreviewModal from "./DocumentPreviewModal";

export default function DocumentSelectionTable({
  documents,
  selectedIds,
  onToggle,
  onSelectAll,
  onDeselectAll,
  onRemove,
  isLoading = false,
}) {
  // Modal state
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

  const handleSelectionChange = (newSelection) => {
    // Get currently selected IDs
    const currentSet = new Set(selectedIds);
    const newSet = new Set(newSelection);

    // Find what was added
    const added = newSelection.filter((id) => !currentSet.has(id));
    // Find what was removed
    const removed = selectedIds.filter((id) => !newSet.has(id));

    if (added.length > 0) {
      added.forEach((id) => onToggle(id));
    }
    if (removed.length > 0) {
      removed.forEach((id) => onToggle(id));
    }
  };

  const columns = React.useMemo(
    () => [
      {
        field: "id",
        headerName: "ID",
        minWidth: 50,
        flex: 0.5,
        editable: false,
      },
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
    ],
    [onRemove],
  );

  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          width: "100%",
        }}
      >
        <DataGrid
          rows={documents}
          columns={columns}
          checkboxSelection
          disableRowSelectionOnClick
          rowSelectionModel={selectedIds}
          onRowSelectionModelChange={handleSelectionChange}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: 5,
              },
            },
          }}
          pageSizeOptions={[5, 10, 25, 50]}
          loading={isLoading}
          slots={{
            loadingOverlay: LinearProgress,
          }}
          sx={{
            backgroundColor: "background.paper",
            borderRadius: 2,
            p: 2,
            "& .MuiDataGrid-row.Mui-selected": {
              backgroundColor: "action.hover",
            },
            "& .MuiDataGrid-virtualScroller": {
              "&::-webkit-scrollbar": {
                width: "10px",
                height: "10px",
              },
              "&::-webkit-scrollbar-track": {
                backgroundColor: "#252836",
                borderRadius: "5px",
              },
              "&::-webkit-scrollbar-thumb": {
                backgroundColor: "#374151",
                borderRadius: "5px",
                border: "2px solid #252836",
                "&:hover": {
                  backgroundColor: "#4a5568",
                },
              },
            },
            // Scrollbar styles for Firefox
            scrollbarWidth: "thin",
            scrollbarColor: "#374151 #252836",
          }}
        />
      </Box>
      <DocumentPreviewModal
        open={previewOpen}
        onClose={handleClosePreview}
        document={previewDoc}
        txtContent={txtContent}
      />
    </>
  );
}

DocumentSelectionTable.propTypes = {
  documents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      file_name: PropTypes.string.isRequired,
      created: PropTypes.oneOfType([
        PropTypes.string,
        PropTypes.instanceOf(Date),
      ]).isRequired,
      preview: PropTypes.string,
      file_type: PropTypes.string,
    }),
  ).isRequired,
  selectedIds: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  ).isRequired,
  onToggle: PropTypes.func.isRequired,
  onSelectAll: PropTypes.func.isRequired,
  onDeselectAll: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
};
