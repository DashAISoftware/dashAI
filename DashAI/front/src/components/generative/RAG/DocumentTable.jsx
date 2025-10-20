import {
  Paper,
  Typography,
  IconButton,
  Tooltip,
  LinearProgress,
  Button,
} from "@mui/material";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";
import { Preview as PreviewIcon, Edit as EditIcon } from "@mui/icons-material";

export default function DocumentTable({
  documents,
  onRemove,
  isLoading = false,
  tableTitle = null,
}) {
  // Format the date to a more readable format
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString();
    } catch (e) {
      return dateString;
    }
  };

  const onPreview = (previewUrl) => {
    if (previewUrl) {
      window.open(previewUrl, "_blank");
    } else {
      console.warn("No preview URL available for this document.");
    }
  };

  const onEdit = (id) => {
    console.warn(
      "Edit functionality is not implemented yet for document ID:",
      id,
    );
  };

  const columns = [
    { field: "id", headerName: "Id", flex: 0.1 },
    { field: "file_name", headerName: "Name", flex: 0.6, minWidth: 150 },
    {
      field: "created",
      headerName: "Added On",
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
      valueGetter: (value, row) => {
        const lastModified = row?.optional_metadata?.last_modified;
        if (!lastModified) return "";
        return formatDate(lastModified);
      },
    },
    {
      field: "actions",
      headerName: "Actions",
      flex: 0.5,
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
            onClick={() => openPreview(params.row.preview)}
          >
            <PreviewIcon />
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="warning"
            onClick={() => onEdit(params.row.id)}
          >
            <EditIcon />
          </Button>
        </div>
      ),
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
