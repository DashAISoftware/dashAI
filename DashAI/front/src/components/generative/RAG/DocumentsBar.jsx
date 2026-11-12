import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import LibraryAddIcon from "@mui/icons-material/LibraryAdd";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DeleteIcon from "@mui/icons-material/Delete";
import VisibilityIcon from "@mui/icons-material/Visibility";
import DescriptionIcon from "@mui/icons-material/Description";
import { useTheme } from "@mui/material/styles";
import { useSnackbar } from "notistack";
import SearchBar from "../../threeSectionLayout/SearchBar";
import DeleteConfirmationModal from "../../threeSectionLayout/DeleteConfirmationModal";
import DocumentGroupList from "./DocumentGroupList";
import DocumentPreviewModal from "./DocumentPreviewModal";
import AddFromDataDialog from "./AddFromDataDialog";
import RAGDocumentUpload from "./RAGDocumentUpload";
import { getApiErrorMessage } from "../../../utils/apiError";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";
import {
  attachSessionDocuments,
  detachSessionDocument,
  listSessionDocuments,
} from "../../../api/rag";

function toRow(doc) {
  return {
    id: doc.id,
    name: doc.name,
    status: doc.status,
    totalPages: doc.total_pages,
    created: doc.created,
    folderId: doc.folder_id ?? null,
    folderName: doc.folder_name ?? null,
  };
}

const LOAD_STATUS = Object.freeze({
  LOADING: "loading",
  READY: "ready",
  ERROR: "error",
});

export default function DocumentsBar({
  sessionId,
  indexStatus,
  onDocumentChange,
  showSearch = true,
}) {
  const { t } = useTranslation("generative");
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const { fetchFolders } = useDatasetsAndNotebooks() ?? {};

  const [documents, setDocuments] = useState([]);
  const [status, setStatus] = useState(LOAD_STATUS.LOADING);
  const [searchQuery, setSearchQuery] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [pendingDetach, setPendingDetach] = useState(null);
  const requestIdRef = useRef(0);

  const indexStateByDocument = useMemo(() => {
    const indexing = indexStatus?.status === "indexing";
    const map = {};
    (indexStatus?.documents ?? []).forEach((entry) => {
      map[entry.document_id] = { ...entry, indexing };
    });
    return map;
  }, [indexStatus]);

  const fetchDocuments = useCallback(async () => {
    if (!sessionId) return;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setStatus(LOAD_STATUS.LOADING);
    try {
      const data = await listSessionDocuments(sessionId);
      if (requestId !== requestIdRef.current) return;
      setDocuments(data.map(toRow));
      setStatus(LOAD_STATUS.READY);
    } catch (error) {
      if (requestId !== requestIdRef.current) return;
      console.error("Failed to fetch documents:", error);
      setStatus(LOAD_STATUS.ERROR);
    }
  }, [sessionId]);

  useEffect(() => {
    setDocuments([]);
    fetchDocuments();
  }, [fetchDocuments]);

  const attachedIds = useMemo(
    () => new Set(documents.map((doc) => doc.id)),
    [documents],
  );

  const filteredDocuments = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return documents;
    return documents.filter((doc) => doc.name.toLowerCase().includes(query));
  }, [documents, searchQuery]);

  const handleAttach = useCallback(
    async (documentIds) => {
      if (documentIds.length === 0) return true;
      try {
        const data = await attachSessionDocuments(sessionId, documentIds);
        setDocuments(data.map(toRow));
        setStatus(LOAD_STATUS.READY);
        enqueueSnackbar(
          t("documentsBar.attached", { count: documentIds.length }),
          { variant: "success" },
        );
        onDocumentChange?.();
        return true;
      } catch (error) {
        console.error("Failed to attach documents:", error);
        enqueueSnackbar(
          getApiErrorMessage(error, t("documentsBar.failedAttach")),
          { variant: "error" },
        );
        return false;
      } finally {
        // A batch upload creates its Data folder before the jobs finish; the
        // app-level folder list has to learn about it for "Add from Data".
        try {
          await fetchFolders?.();
        } catch {
          // Best effort: the Data module refreshes folders when it mounts.
        }
      }
    },
    [sessionId, enqueueSnackbar, t, onDocumentChange, fetchFolders],
  );

  const handleConfirmDetach = async () => {
    const doc = pendingDetach;
    setPendingDetach(null);
    if (!doc) return;
    try {
      await detachSessionDocument(sessionId, doc.id);
      setDocuments((previous) => previous.filter((row) => row.id !== doc.id));
      enqueueSnackbar(t("documentsBar.detached", { file: doc.name }), {
        variant: "success",
      });
      onDocumentChange?.();
    } catch (error) {
      console.error("Failed to detach document:", error);
      enqueueSnackbar(
        getApiErrorMessage(error, t("documentsBar.failedDetach")),
        { variant: "error" },
      );
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        height: "100%",
        width: "100%",
        minWidth: 0,
        maxWidth: "100%",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          flexShrink: 0,
          py: 2,
          px: 4,
          mx: 4,
          mt: 4,
          mb: 2,
        }}
      >
        <DescriptionIcon
          sx={{ color: theme.palette.primary.main, mr: 4, fontSize: 20 }}
        />
        <Typography
          noWrap
          color="text.primary"
          sx={{ ...theme.typography.h5, flex: 1 }}
        >
          {t("documentsBar.title")}
        </Typography>
        <Typography
          variant="body2"
          component="div"
          sx={{
            bgcolor: "primary.main",
            color: "primary.contrastText",
            borderRadius: 10,
            minWidth: 20,
            px: 0.75,
            height: 20,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {documents.length > 99 ? "99+" : documents.length}
        </Typography>
      </Box>

      {/* Kept side by side as in the original documents panel: the two primary
          actions read as one row instead of a stack. */}
      <Stack direction="row" spacing={1} sx={{ flexShrink: 0, px: 4, pb: 2 }}>
        <Button
          variant="contained"
          fullWidth
          startIcon={<LibraryAddIcon />}
          onClick={() => setPickerOpen(true)}
        >
          {t("documentsBar.addFromData")}
        </Button>
        <Button
          variant="outlined"
          fullWidth
          startIcon={<UploadFileIcon />}
          onClick={() => setUploadOpen(true)}
        >
          {t("documentsBar.uploadToData")}
        </Button>
      </Stack>

      {/* {showSearch && documents.length > 1 && (
        <Box sx={{ px: 4, pb: 2, flexShrink: 0 }}>
          <SearchBar
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            onClear={() => setSearchQuery("")}
            placeholder={t("documentsBar.searchPlaceholder")}
          />
        </Box>
      )} */}

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          overflowX: "hidden",
          overscrollBehavior: "contain",
          px: 4,
          pb: 2,
          width: "100%",
          minWidth: 0,
        }}
      >
        {status === LOAD_STATUS.LOADING ? (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              p: 2,
            }}
          >
            {reduceMotion ? (
              <Typography variant="body2" color="text.secondary" role="status">
                {t("common:loading")}
              </Typography>
            ) : (
              <CircularProgress size={28} aria-label={t("common:loading")} />
            )}
          </Box>
        ) : status === LOAD_STATUS.ERROR ? (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={fetchDocuments}>
                {t("documentsBar.retry")}
              </Button>
            }
          >
            {t("documentsBar.failedFetch")}
          </Alert>
        ) : filteredDocuments.length > 0 ? (
          <DocumentGroupList
            documents={filteredDocuments}
            indexStateByDocument={indexStateByDocument}
            onDocumentClick={setPreviewDoc}
            renderActions={(doc) => (
              <>
                <Tooltip title={t("documentsBar.detach")}>
                  <IconButton
                    size="small"
                    onClick={() => setPendingDetach(doc)}
                    aria-label={t("documentsBar.detach")}
                  >
                    <DeleteIcon fontSize="small" color="error" />
                  </IconButton>
                </Tooltip>
              </>
            )}
          />
        ) : (
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: 1,
              height: "100%",
              p: 2,
            }}
          >
            <Typography
              variant="body2"
              sx={{ color: "text.secondary", textAlign: "center" }}
            >
              {searchQuery
                ? t("documentsBar.noDocumentsFound")
                : t("documentsBar.noDocumentsInSession")}
            </Typography>
          </Box>
        )}
      </Box>

      {pickerOpen && (
        <AddFromDataDialog
          open
          onClose={() => setPickerOpen(false)}
          attachedIds={attachedIds}
          onConfirm={handleAttach}
        />
      )}

      <RAGDocumentUpload
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onReady={handleAttach}
      />

      <DocumentPreviewModal
        open={previewDoc !== null}
        onClose={() => setPreviewDoc(null)}
        document={previewDoc}
      />

      <DeleteConfirmationModal
        open={pendingDetach !== null}
        onClose={() => setPendingDetach(null)}
        onConfirm={handleConfirmDetach}
        content={pendingDetach?.name}
        warning={t("documentsBar.detachWarning")}
      />
    </Box>
  );
}

DocumentsBar.propTypes = {
  sessionId: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    .isRequired,
  indexStatus: PropTypes.object,
  onDocumentChange: PropTypes.func,
  showSearch: PropTypes.bool,
};
