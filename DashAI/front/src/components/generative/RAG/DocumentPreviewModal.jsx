import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import { createPortal } from "react-dom";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import DocumentRenderer from "../../documents/DocumentRenderer";
import {
  LoadMoreFooter,
  usePagedContent,
} from "../../documents/DocumentReader";
import RAGAdvancedDialog from "../../../pages/generative/RAGSession/advanced/RAGAdvancedDialog";
import { getDocument, getDocumentContent } from "../../../api/documents";
import { DOCUMENT_STATUS } from "../../../hooks/datasets/useDocuments";

function CenteredState({ children }) {
  return (
    <Box
      sx={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 2,
        p: 4,
        textAlign: "center",
      }}
    >
      {children}
    </Box>
  );
}

function DocumentPreviewBody({ dataDocument }) {
  const { t } = useTranslation(["datasets"]);
  const documentId = dataDocument.id;
  const fetchPage = useCallback(
    (contentType, offset, limit) =>
      getDocumentContent(documentId, contentType, offset, limit),
    [documentId],
  );
  const content = usePagedContent(fetchPage, "all", true);

  const isEmpty = Object.values(dataDocument.content_counts || {}).every(
    (count) => !count,
  );

  if (content.items.length === 0) {
    if (content.failed)
      return (
        <CenteredState>
          <Alert severity="error">{t("datasets:document.loadingFailed")}</Alert>
        </CenteredState>
      );
    return (
      <CenteredState>
        {isEmpty ? (
          <Typography variant="body2" color="text.secondary">
            {t("datasets:document.noContent")}
          </Typography>
        ) : (
          <CircularProgress />
        )}
      </CenteredState>
    );
  }

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        overflowY: "auto",
        overscrollBehavior: "contain",
        p: { xs: 2, md: 4 },
      }}
    >
      <Box
        sx={{
          maxWidth: 860,
          mx: "auto",
          bgcolor: "background.box",
          borderRadius: 1,
          p: { xs: 2, md: 4 },
        }}
      >
        <DocumentRenderer
          items={content.items}
          mode="read"
          totalPages={dataDocument.total_pages}
        />
      </Box>
      {content.failed && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {t("datasets:document.loadingFailed")}
        </Alert>
      )}
      <LoadMoreFooter content={content} />
    </Box>
  );
}

export default function DocumentPreviewModal({ open, onClose, document }) {
  const { t } = useTranslation(["generative", "datasets", "common"]);
  const navigate = useNavigate();
  const [dataDocument, setDataDocument] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    if (!open || !document) {
      setDataDocument(null);
      setStatus("loading");
      return undefined;
    }
    let cancelled = false;
    setStatus("loading");
    getDocument(document.id)
      .then((loaded) => {
        if (cancelled) return;
        setDataDocument(loaded);
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) {
          setDataDocument(null);
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, document]);

  const openInData = () => {
    onClose();
    navigate(`/app/data/documents/${document.id}`);
  };

  const renderContent = () => {
    if (status === "loading")
      return (
        <CenteredState>
          <CircularProgress aria-label={t("common:loading")} />
        </CenteredState>
      );
    if (status === "error")
      return (
        <CenteredState>
          <Alert severity="error">
            {t("generative:rag.documentPreview.loadFailed")}
          </Alert>
        </CenteredState>
      );
    if (dataDocument.status === DOCUMENT_STATUS.ERROR)
      return (
        <CenteredState>
          <Alert severity="error">{t("datasets:document.errorMessage")}</Alert>
        </CenteredState>
      );
    if (dataDocument.status !== DOCUMENT_STATUS.FINISHED)
      return (
        <CenteredState>
          <CircularProgress />
          <Typography>{t("datasets:document.processingTitle")}</Typography>
        </CenteredState>
      );
    return (
      <DocumentPreviewBody key={dataDocument.id} dataDocument={dataDocument} />
    );
  };

  const dialogContent = (
    <RAGAdvancedDialog
      open={open}
      onClose={onClose}
      title={document?.name ?? t("generative:rag.documentPreview.title")}
      maxWidth="lg"
      minHeight={0}
      paperSx={{
        height: "85vh",
        bgcolor: "background.paper",
        backgroundImage: "none",
      }}
      contentSx={{
        p: 0,
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        overflow: "hidden",
      }}
      actions={
        <>
          <Button
            startIcon={<OpenInNewIcon />}
            disabled={!document}
            onClick={openInData}
          >
            {t("generative:rag.documentPreview.openInData")}
          </Button>
          <Button variant="outlined" onClick={onClose}>
            {t("common:close")}
          </Button>
        </>
      }
    >
      {renderContent()}
    </RAGAdvancedDialog>
  );

  return createPortal(dialogContent, globalThis.document.body);
}

CenteredState.propTypes = {
  children: PropTypes.node,
};

DocumentPreviewBody.propTypes = {
  dataDocument: PropTypes.object.isRequired,
};

DocumentPreviewModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  document: PropTypes.object,
};
