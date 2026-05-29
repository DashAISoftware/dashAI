import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

function formatRows(n) {
  if (!n) return "?";
  if (n >= 1_000_000) return `~${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `~${Math.round(n / 1_000)}k`;
  return `${n}`;
}

export default function ComputeMetadataConfirmDialog({
  open,
  colCount,
  estRows,
  onComputeAnyway,
  onSkipMetadata,
}) {
  const { t } = useTranslation(["datasets", "common"]);

  return (
    <Dialog open={open} onClose={onSkipMetadata}>
      <DialogTitle>{t("datasets:computeMetadata.confirmTitle")}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          {t("datasets:computeMetadata.confirmBody", {
            colCount,
            estRows: formatRows(estRows),
          })}
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onSkipMetadata} color="inherit">
          {t("datasets:computeMetadata.skipButton")}
        </Button>
        <Button onClick={onComputeAnyway} variant="contained">
          {t("datasets:computeMetadata.computeButton")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

ComputeMetadataConfirmDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  colCount: PropTypes.number,
  estRows: PropTypes.number,
  onComputeAnyway: PropTypes.func.isRequired,
  onSkipMetadata: PropTypes.func.isRequired,
};
