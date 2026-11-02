import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

/**
 * The dialog shell every RAG advanced editor wears.
 *
 * Chunking, retriever, generator and query transformation are four different
 * forms with one job: edit a slice of the pipeline and return to the panel.
 * Giving them a single shell keeps the title row, the close affordance, the
 * scroll owner and the action row in the same place in all four, so moving
 * between them never moves the thing the user is aiming at.
 *
 * The close control lives in the title row rather than only in the actions:
 * the primary action can be disabled (an incomplete form), and a modal with no
 * enabled way out at its foot reads as a dead end.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {Function} props.onClose - Called when the dialog asks to close.
 * @param {string}   props.title - The dialog heading.
 * @param {node}     props.children - The dialog body.
 * @param {node}     [props.actions] - Footer controls, usually Close + Done.
 * @param {"xs"|"sm"|"md"|"lg"|"xl"|false} [props.maxWidth] - MUI dialog
 *   width, or `false` to let `paperSx` own the cap.
 * @param {number}   [props.minHeight] - Minimum height of the dialog paper.
 * @param {object}   [props.contentSx] - Extra styles for the scrolling body.
 * @param {object}   [props.paperSx] - Extra styles for the dialog paper.
 * @param {object}   [props.dialogProps] - Extra props for the MUI Dialog
 *   itself, for the rare dialog that has to stack above another one.
 * @returns {JSX.Element} The dialog.
 */
export default function RAGAdvancedDialog({
  open,
  onClose,
  title,
  children,
  actions,
  maxWidth = "md",
  minHeight = 500,
  contentSx,
  paperSx,
  dialogProps,
}) {
  const { t } = useTranslation(["common"]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={maxWidth}
      fullWidth
      PaperProps={{
        sx: {
          // Below `sm` the dialog fills most of the (short) viewport and the
          // body scrolls; a fixed 500px floor would push the actions off it.
          minHeight: { xs: 0, sm: minHeight },
          ...paperSx,
        },
      }}
      {...dialogProps}
    >
      <DialogTitle
        component="div"
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          bgcolor: "background.paper",
        }}
      >
        <Typography
          variant="h6"
          component="h2"
          sx={{ flex: 1, minWidth: 0, overflowWrap: "anywhere" }}
        >
          {title}
        </Typography>
        <IconButton
          onClick={onClose}
          size="small"
          aria-label={t("common:close")}
          sx={{ color: "text.secondary", flexShrink: 0, mr: -0.5 }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent
        dividers
        sx={{
          bgcolor: "background.paper",
          // The body owns the scroll of a tall form; keep that scroll inside
          // the dialog instead of letting it chain to the page behind it.
          overscrollBehavior: "contain",
          ...contentSx,
        }}
      >
        {children}
      </DialogContent>

      {actions && (
        <DialogActions sx={{ p: 2, gap: 1, bgcolor: "background.paper" }}>
          {actions}
        </DialogActions>
      )}
    </Dialog>
  );
}

RAGAdvancedDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
  actions: PropTypes.node,
  maxWidth: PropTypes.oneOf(["xs", "sm", "md", "lg", "xl", false]),
  minHeight: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  contentSx: PropTypes.object,
  paperSx: PropTypes.object,
  dialogProps: PropTypes.object,
};
