import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { Button } from "@mui/material";
import RAGAdvancedDialog from "../../../pages/generative/RAGSession/advanced/RAGAdvancedDialog";

/**
 * Dialog shell shared by the document pickers.
 *
 * Both entry points (creating a session and attaching from an existing one)
 * present the same sized dialog with the same footer, so only the picker body
 * differs.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {Function} props.onClose - Called when the dialog asks to close.
 * @param {string}   props.title - The dialog heading.
 * @param {node}     props.children - The dialog body.
 * @param {node}     props.confirmLabel - The confirm button label.
 * @param {boolean}  props.confirmDisabled - Disables the confirm button.
 * @param {boolean}  [props.confirming] - Shows a spinner and blocks closing.
 * @param {Function} props.onConfirm - Called when the confirm button is used.
 * @returns {JSX.Element} The dialog.
 */
export default function DocumentPickerDialog({
  open,
  onClose,
  title,
  children,
  confirmLabel,
  confirmDisabled,
  confirming = false,
  onConfirm,
}) {
  const { t } = useTranslation(["common"]);

  /**
   * Ignores close requests while the confirm action is in flight.
   */
  const handleClose = () => {
    if (confirming) return;
    onClose();
  };

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={handleClose}
      closeDisabled={confirming}
      dialogProps={{ disableEscapeKeyDown: confirming }}
      title={title}
      maxWidth="lg"
      minHeight={0}
      paperSx={{
        height: "80vh",
        bgcolor: "background.paper",
        backgroundImage: "none",
      }}
      contentSx={{
        p: 0,
        display: "flex",
        flexDirection: { xs: "column", md: "row" },
        minHeight: 0,
        overflow: "hidden",
      }}
      actions={
        <>
          <Button onClick={handleClose} disabled={confirming}>
            {t("common:cancel")}
          </Button>
          <Button
            variant="contained"
            loading={confirming}
            disabled={confirmDisabled}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      {children}
    </RAGAdvancedDialog>
  );
}

DocumentPickerDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
  confirmLabel: PropTypes.node.isRequired,
  confirmDisabled: PropTypes.bool.isRequired,
  confirming: PropTypes.bool,
  onConfirm: PropTypes.func.isRequired,
};
