import { memo, useState } from "react";
import PropTypes from "prop-types";
import { Chip, Menu, MenuItem, Tooltip } from "@mui/material";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";

import { updateColumnEncoder } from "../../../api/datasets";
import { ENCODER_OPTIONS } from "./operators";

function useEncoderLabel() {
  const { t } = useTranslation(["common"]);
  return (enc) => {
    if (enc === "one_hot") return t("common:encoderOneHot");
    if (enc === "label") return t("common:encoderLabel");
    return enc ?? "-";
  };
}

const LeanEncoderChip = memo(function LeanEncoderChip({
  columnName,
  encoder,
  datasetId,
  onChanged,
}) {
  const [anchor, setAnchor] = useState(null);
  const [pending, setPending] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["common", "datasets"]);
  const encoderLabel = useEncoderLabel();

  const handleSelect = async (next) => {
    setAnchor(null);
    if (next === encoder) return;
    setPending(true);
    try {
      await updateColumnEncoder(datasetId, columnName, next);
      if (onChanged) onChanged();
    } catch (e) {
      enqueueSnackbar(
        t("datasets:table.failedToUpdateEncoder", { columnName }),
        { variant: "error" },
      );
    } finally {
      setPending(false);
    }
  };

  return (
    <>
      <Tooltip title={t("common:changeEncoder")} arrow>
        <span style={{ display: "inline-flex" }}>
          <Chip
            label={pending ? "..." : encoderLabel(encoder)}
            size="small"
            disabled={pending}
            onClick={(e) => {
              e.stopPropagation();
              setAnchor(e.currentTarget);
            }}
            aria-label={t("common:encoder")}
            sx={{
              fontSize: "0.65rem",
              height: "18px",
              cursor: "pointer",
            }}
          />
        </span>
      </Tooltip>
      {anchor && (
        <Menu
          anchorEl={anchor}
          open={Boolean(anchor)}
          onClose={() => setAnchor(null)}
        >
          {ENCODER_OPTIONS.map((opt) => (
            <MenuItem
              key={opt}
              selected={opt === encoder}
              onClick={() => handleSelect(opt)}
              sx={{ fontSize: "0.85rem" }}
            >
              {encoderLabel(opt)}
            </MenuItem>
          ))}
        </Menu>
      )}
    </>
  );
});

LeanEncoderChip.propTypes = {
  columnName: PropTypes.string.isRequired,
  encoder: PropTypes.string,
  datasetId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
  onChanged: PropTypes.func,
};

export default LeanEncoderChip;
