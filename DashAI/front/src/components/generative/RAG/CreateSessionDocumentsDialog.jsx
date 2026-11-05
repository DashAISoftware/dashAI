import { useMemo } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { Box } from "@mui/material";
import { useDatasetsAndNotebooks } from "../../custom/contexts/DatasetsAndNotebooksContext";
import useDocumentFolderSelection from "./useDocumentFolderSelection";
import DocumentFolderPicker from "./DocumentFolderPicker";
import DocumentPickerDialog from "./DocumentPickerDialog";

/**
 * Lets the user pick folders and documents while creating a RAG session.
 *
 * The library and folders come from the Data context, so this dialog is mounted
 * only while it is open: pages that never open it do not need the provider.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {Function} props.onClose - Called when the dialog asks to close.
 * @param {Function} props.onConfirm - Receives the selected ids and a summary
 *   `{ folderCount }`.
 * @param {Array}    [props.initialSelectedIds] - Ids to preselect.
 * @returns {JSX.Element}
 */
export default function CreateSessionDocumentsDialog({
  open,
  onClose,
  onConfirm,
  initialSelectedIds = [],
}) {
  const { t } = useTranslation(["generative", "common"]);
  const context = useDatasetsAndNotebooks();
  if (!context) {
    throw new Error(
      "CreateSessionDocumentsDialog must be used within DatasetsAndNotebooksProvider",
    );
  }
  const { documents = [], folders = [] } = context;
  const attachedIds = useMemo(() => new Set(), []);
  const selection = useDocumentFolderSelection({
    documents,
    folders,
    attachedIds,
    initialSelectedIds,
  });

  /**
   * Clears the pending selection and closes the dialog.
   */
  const handleClose = () => {
    selection.clear();
    onClose();
  };

  /**
   * Hands the selected ids to the page and closes the dialog.
   *
   * The selection is copied before clearing so the page receives the ids even
   * though the hook state is reset on the way out.
   */
  const handleConfirm = () => {
    const ids = [...selection.selectedIdsArray];
    const meta = { folderCount: selection.selectedFolderCount };
    onConfirm(ids, meta);
    handleClose();
  };

  return (
    <DocumentPickerDialog
      open={open}
      onClose={handleClose}
      title={t("generative:documentPicker.title")}
      confirmLabel={
        selection.selectedCount === 0
          ? t("generative:documentPicker.selectDocuments")
          : t("generative:documentPicker.addSelected", {
              count: selection.selectedCount,
            })
      }
      confirmDisabled={selection.selectedCount === 0}
      onConfirm={handleConfirm}
    >
      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          minHeight: 0,
          display: "flex",
          p: 2,
        }}
      >
        <DocumentFolderPicker selection={selection} />
      </Box>
    </DocumentPickerDialog>
  );
}

CreateSessionDocumentsDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  initialSelectedIds: PropTypes.arrayOf(PropTypes.number),
};
