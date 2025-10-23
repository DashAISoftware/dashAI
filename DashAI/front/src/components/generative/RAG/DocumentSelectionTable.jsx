import React from "react";
import { Box, IconButton, Tooltip, LinearProgress } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import VisibilityIcon from "@mui/icons-material/Visibility";
import PropTypes from "prop-types";
import { formatDate } from "../../../utils";
import DeleteItemModal from "../../custom/DeleteItemModal";

export default function DocumentSelectionTable({
  documents,
  selectedIds,
  onToggle,
  onSelectAll,
  onDeselectAll,
  onRemove,
  isLoading = false,
}) {
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
              onClick={() => {
                if (params.row.preview) {
                  window.open(params.row.preview, "_blank");
                } else {
                  console.warn("No preview URL available for this document.");
                }
              }}
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
    <Box
      sx={{
        backgroundColor: "background.paper",
        borderRadius: 2,
        p: 2,
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
  );
}

DocumentSelectionTable.propTypes = {
  documents: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      createdAt: PropTypes.string.isRequired,
      preview: PropTypes.string,
    }),
  ).isRequired,
  selectedIds: PropTypes.arrayOf(PropTypes.string).isRequired,
  onToggle: PropTypes.func.isRequired,
  onSelectAll: PropTypes.func.isRequired,
  onDeselectAll: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
};
