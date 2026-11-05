import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { Box, Chip, Divider, Typography } from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import DocumentIcon from "@mui/icons-material/Description";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";
import { DOCUMENT_STATUS } from "../../../hooks/datasets/useDocuments";
import { formatDate } from "../../../pages/results/constants/formatDate";
import useDocumentFolderSelection from "./useDocumentFolderSelection";
import DocumentFolderPicker from "./DocumentFolderPicker";
import DocumentPickerDialog from "./DocumentPickerDialog";
import { documentStatusChip } from "./documentStatusChip";

function DetailRow({ label, value }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 2fr) minmax(0, 3fr)",
        gap: 1,
        py: 0.75,
      }}
    >
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="caption"
        sx={{ wordBreak: "break-word", fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </Typography>
    </Box>
  );
}

function DocumentDetails({ doc, attached }) {
  const { t } = useTranslation(["generative", "datasets", "common"]);

  if (!doc) {
    return (
      <Box
        sx={{
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 1,
          px: 2,
          textAlign: "center",
          color: "text.secondary",
        }}
      >
        <InfoOutlinedIcon />
        <Typography variant="body2">
          {t("generative:documentsBar.selectToSeeDetails")}
        </Typography>
      </Box>
    );
  }

  const counts = doc.content_counts || {};
  const finished = doc.status === DOCUMENT_STATUS.FINISHED;
  const chip = documentStatusChip(doc, attached, t);
  const rows = [
    [t("datasets:document.fileName"), doc.file_name],
    [t("datasets:document.loader"), doc.dataloader],
    [t("datasets:document.pages"), finished ? doc.total_pages : null],
    [t("datasets:document.textCount"), finished ? (counts.Text ?? 0) : null],
    [t("datasets:document.imageCount"), finished ? (counts.Image ?? 0) : null],
    [t("common:created"), doc.created && formatDate(doc.created)],
    [
      t("common:lastModified"),
      doc.last_modified && formatDate(doc.last_modified),
    ],
  ].filter(
    ([, value]) => value !== null && value !== undefined && value !== "",
  );

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 1,
          pt: 1,
        }}
      >
        <DocumentIcon sx={{ fontSize: 72, color: "text.secondary" }} />
        <Typography
          variant="subtitle1"
          sx={{ fontWeight: 600, textAlign: "center", wordBreak: "break-word" }}
        >
          {doc.name}
        </Typography>
        {chip && (
          <Chip
            size="small"
            variant="outlined"
            color={chip.color}
            label={chip.label}
          />
        )}
      </Box>
      <Divider />
      <Box>
        <Typography
          variant="overline"
          color="text.secondary"
          sx={{ display: "block", lineHeight: 2 }}
        >
          {t("datasets:document.details")}
        </Typography>
        {rows.map(([label, value]) => (
          <DetailRow key={label} label={label} value={value} />
        ))}
      </Box>
    </Box>
  );
}

export default function AddFromDataDialog({
  open,
  onClose,
  attachedIds,
  onConfirm,
}) {
  const { t } = useTranslation(["generative", "datasets", "common"]);
  const context = useDatasetsAndNotebooks();
  if (!context) {
    throw new Error(
      "AddFromDataDialog must be used within DatasetsAndNotebooksProvider",
    );
  }
  const { documents = [], folders = [] } = context;
  const [submitting, setSubmitting] = useState(false);
  const selection = useDocumentFolderSelection({
    documents,
    folders,
    attachedIds,
  });

  const focusedDoc = useMemo(() => {
    const byId = new Map(documents.map((doc) => [doc.id, doc]));
    if (selection.focusedId != null) {
      const focused = byId.get(selection.focusedId);
      if (focused) return focused;
    }
    return byId.get(selection.selectedIdsArray[0]) ?? null;
  }, [documents, selection.focusedId, selection.selectedIdsArray]);

  /**
   * Closes the dialog without discarding the selection while an attach runs.
   */
  const handleClose = () => {
    if (submitting) return;
    selection.clear();
    onClose();
  };

  /**
   * Sends the selected ids and closes only when the attach succeeds.
   *
   * `onConfirm` returns false when the attach failed; the dialog then stays
   * open with the selection intact so the user can retry or adjust it.
   */
  const handleConfirm = async () => {
    if (submitting) return;
    const ids = [...selection.selectedIdsArray];
    setSubmitting(true);
    try {
      const accepted = await onConfirm(ids);
      if (accepted === false) return;
      selection.clear();
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <DocumentPickerDialog
      open={open}
      onClose={handleClose}
      title={t("generative:documentsBar.addFromDataTitle")}
      confirmLabel={
        selection.selectedCount === 0
          ? t("generative:documentPicker.selectDocuments")
          : t("generative:documentPicker.addSelected", {
              count: selection.selectedCount,
            })
      }
      confirmDisabled={selection.selectedCount === 0 || submitting}
      confirming={submitting}
      onConfirm={handleConfirm}
    >
      <Box
        sx={{
          flex: { xs: 1, md: 3 },
          minWidth: 0,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          p: 2,
        }}
      >
        <DocumentFolderPicker
          selection={selection}
          onFocusDocument={(doc) => selection.setFocusedId(doc.id)}
        />
      </Box>
      <Box
        sx={{
          flex: { xs: "0 0 38%", md: 1 },
          minWidth: 0,
          minHeight: 0,
          borderTop: { xs: 1, md: 0 },
          borderLeft: { xs: 0, md: 1 },
          borderColor: "divider",
          overflowY: "auto",
          overscrollBehavior: "contain",
          p: 2,
        }}
      >
        <DocumentDetails
          doc={focusedDoc}
          attached={focusedDoc ? attachedIds.has(focusedDoc.id) : false}
        />
      </Box>
    </DocumentPickerDialog>
  );
}

DetailRow.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.node.isRequired,
};

DocumentDetails.propTypes = {
  doc: PropTypes.object,
  attached: PropTypes.bool.isRequired,
};

AddFromDataDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  attachedIds: PropTypes.instanceOf(Set).isRequired,
  onConfirm: PropTypes.func.isRequired,
};
