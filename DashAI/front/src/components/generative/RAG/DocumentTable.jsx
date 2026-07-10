import React, { useState } from "react";
import Dialog from "@mui/material/Dialog";
import Upload from "../../shared/Upload";
import { addDocument } from "../../../api/rag";
import AddIcon from "@mui/icons-material/AddCircleOutline";
import {
  Paper,
  Typography,
  IconButton,
  Tooltip,
  LinearProgress,
  Button,
  Grid,
} from "@mui/material";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { formatDate } from "../../../utils";
import DeleteItemModal from "../../custom/DeleteItemModal";
import DocumentPreviewModal from "./DocumentPreviewModal";
import { normalizeUrl } from "../../../utils/urlUtils";
import { useTranslation } from "react-i18next";

export default function DocumentTable({
  documents,
  onRemove,
  onAddDocument,
  isLoading = false,
  tableTitle = null,
  showTableTitle = false,
}) {
  const { t } = useTranslation(["generative", "common"]);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [txtContent, setTxtContent] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);

  const handleOpenPreview = async (doc) => {
    setPreviewDoc(doc);
    if (doc.file_type === "txt" && doc.preview) {
      try {
        const res = await fetch(normalizeUrl(doc.preview));
        const text = await res.text();
        setTxtContent(text);
      } catch (e) {
        setTxtContent("Error loading TXT file");
      }
    }
    setPreviewOpen(true);
  };

  const handleRemoveDocument = (id) => {
    if (onRemove) onRemove(id);
  };

  const handleFileUpload = async (files, url) => {
    if (!files) return;
    const fileList = Array.isArray(files) ? files : [files];
    for (const file of fileList) {
      const docToAdd = {
        file,
        optional_metadata: {
          name: file.name,
          source: url || "local_upload",
        },
      };
      try {
        const savedDoc = await addDocument(docToAdd);
        if (onAddDocument) onAddDocument(savedDoc);
      } catch (error) {}
    }
    setUploadOpen(false);
  };

  const handleClosePreview = () => {
    setPreviewOpen(false);
    setPreviewDoc(null);
    setTxtContent("");
  };

  const columns = [
    { field: "id", headerName: t("generative:rag.documents.table.id"), flex: 0.1, editable: false },
    {
      field: "file_name",
      headerName: t("generative:rag.documents.table.name"),
      flex: 0.6,
      editable: false,
    },
    {
      field: "created",
      headerName: t("generative:rag.documents.table.created"),
      flex: 0.4,
      editable: false,
      valueGetter: (value) => formatDate(value),
    },
    {
      field: "last_modified",
      headerName: t("generative:rag.documents.table.lastModified"),
      flex: 0.4,
      editable: false,
      valueGetter: (value, row) => {
        return row?.optional_metadata?.last_modified
          ? formatDate(row.optional_metadata.last_modified)
          : t("common:na");
      },
    },
    {
      field: "actions",
      type: "actions",
      headerName: t("generative:rag.documents.table.actions"),
      flex: 0.3,
      getActions: (params) => [
        <Tooltip title={t("generative:rag.documents.table.preview")} key="preview">
          <IconButton
            size="small"
            onClick={() => handleOpenPreview(params.row)}
          >
            <VisibilityIcon fontSize="small" />
          </IconButton>
        </Tooltip>,
        <DeleteItemModal
          key="delete-button"
          deleteFromTable={() => handleRemoveDocument(params.row.id)}
          item="document"
        />,
      ],
    },
  ];

  return (
    <Paper sx={{ py: 4, px: 4 }}>
      {showTableTitle ? (
        <Grid
          container
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Typography variant="h5" component="h2">
            {tableTitle || t("generative:rag.documents.table.currentDocuments")}
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setUploadOpen(true)}
          >
            {t("generative:rag.documents.table.addDocument")}
          </Button>
        </Grid>
      ) : (
        <Grid
          container
          justifyContent="flex-end"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setUploadOpen(true)}
          >
            {t("generative:rag.documents.table.addDocument")}
          </Button>
        </Grid>
      )}
      {documents.length === 0 && !isLoading ? (
        <Typography
          variant="body1"
          color="warning.main"
          textAlign="center"
          mt={16}
          mx={"auto "}
        >
          {t("generative:rag.documents.table.noDocumentsAvailable")}
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
      <Dialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <Upload
          onFileUpload={handleFileUpload}
          multiple={true}
          emptyUploadText={t("generative:rag.documents.table.emptyUploadText")}
        />
      </Dialog>
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
  tableTitle: PropTypes.string,
  showTableTitle: PropTypes.bool,
};
