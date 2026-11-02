import React from "react";
import PropTypes from "prop-types";
import { Box, Button, Stack, Tooltip, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import SplitsCard from "./SplitsCard";
import { SPLIT_ROLES } from "../../../utils/splitPreview";

const LEGEND_ORDER = [
  SPLIT_ROLES.TRAIN,
  SPLIT_ROLES.VALIDATION,
  SPLIT_ROLES.TEST,
  SPLIT_ROLES.UNUSED,
];

const roleColors = (theme) => {
  const [green, , orange] = theme.palette.chart?.palette ?? [];
  return {
    [SPLIT_ROLES.TRAIN]: theme.palette.primary.main,
    [SPLIT_ROLES.VALIDATION]: orange ?? theme.palette.warning.main,
    [SPLIT_ROLES.TEST]: green ?? theme.palette.success.main,
    [SPLIT_ROLES.UNUSED]: theme.palette.action.disabledBackground,
  };
};

const asPercent = (fraction) => Math.round((fraction ?? 0) * 100);

/**
 * Draw the preview of a split, as the splitter computed it on the dataset
 * (POST /splitter/preview). Nothing here is computed: the bars, their labels,
 * the shares and the notes all come with the preview.
 *
 * Without a preview it says why: it is being drawn, the splitter has none,
 * the splitter refuses the parameters (`failure.invalid`, explained under its
 * form), or the preview could not be computed, which can be retried and does
 * not keep the wizard from going on.
 */
function SplitPreview({
  preview,
  loading,
  failure,
  onRetry,
  description,
  splitterDescription,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["experiments", "common"]);

  const explainers = [description, splitterDescription].filter(Boolean);

  const colors = roleColors(theme);

  const roleLabel = (role) =>
    role === SPLIT_ROLES.UNUSED
      ? t("experiments:splitPreview.unused")
      : t(`common:${role}`);

  if (!preview) {
    return (
      <SplitsCard label={t("experiments:splitPreview.title")}>
        <Stack spacing={2}>
          {explainers.map((explainer) => (
            <Typography
              key={explainer}
              variant="caption"
              color="text.secondary"
            >
              {explainer}
            </Typography>
          ))}
          <Typography variant="caption" color="text.secondary">
            {loading
              ? t("experiments:splitPreview.loading")
              : failure?.invalid
                ? t("experiments:splitPreview.invalid")
                : failure
                  ? t("experiments:splitPreview.failed", {
                      reason: failure.reason,
                    })
                  : t("experiments:splitPreview.unavailable")}
          </Typography>
          {!loading && failure && !failure.invalid && onRetry && (
            <Box>
              <Button size="small" onClick={onRetry}>
                {t("experiments:splitPreview.retry")}
              </Button>
            </Box>
          )}
        </Stack>
      </SplitsCard>
    );
  }

  const { rows, notes, shares } = preview;
  // The legend the preview carries, when the shares would not say it (a
  // backtest counts its windows in steps); otherwise each share as a
  // percentage.
  const legend =
    preview.legend ??
    LEGEND_ORDER.filter((role) => (shares[role] ?? 0) > 0.0001).map((role) => ({
      role,
      text: `${roleLabel(role)} ${asPercent(shares[role])}%`,
    }));
  const legendText = (entry) =>
    entry.text ??
    t(`experiments:splitPreview.legend.${entry.key}`, {
      ...entry.values,
      role: roleLabel(entry.role),
    });

  return (
    <SplitsCard label={t("experiments:splitPreview.title")}>
      <Stack spacing={3}>
        {explainers.length > 0 && (
          <Stack spacing={2}>
            {explainers.map((explainer) => (
              <Typography
                key={explainer}
                variant="caption"
                color="text.secondary"
              >
                {explainer}
              </Typography>
            ))}
          </Stack>
        )}

        {rows.length > 0 && (
          <Stack spacing={1}>
            {rows.map((row) =>
              row.ellipsis ? (
                <Box
                  key={row.key}
                  sx={{ display: "flex", alignItems: "center", gap: 2 }}
                >
                  <Box sx={{ width: 58, flexShrink: 0 }} />
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ lineHeight: 1 }}
                  >
                    {t(`experiments:splitPreview.${row.label}`, {
                      hidden: row.hidden_count,
                    })}
                  </Typography>
                </Box>
              ) : (
                <Box
                  key={row.key}
                  sx={{ display: "flex", alignItems: "center", gap: 2 }}
                >
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    noWrap
                    sx={{ width: 58, flexShrink: 0, fontSize: "0.68rem" }}
                  >
                    {t(
                      `experiments:splitPreview.${row.label}`,
                      row.label_values,
                    )}
                  </Typography>
                  <Box
                    sx={{
                      display: "flex",
                      flex: 1,
                      height: 14,
                      borderRadius: 0.5,
                      overflow: "hidden",
                      backgroundColor: colors[SPLIT_ROLES.UNUSED],
                    }}
                  >
                    {row.segments.map((piece, index) => (
                      <Tooltip
                        key={`${row.key}-${index}`}
                        title={`${roleLabel(piece.role)} ${asPercent(
                          piece.fraction,
                        )}%`}
                        arrow
                      >
                        <Box
                          sx={{
                            width: `${piece.fraction * 100}%`,
                            minWidth: 2,
                            backgroundColor: colors[piece.role],
                            borderRight:
                              index < row.segments.length - 1
                                ? `1px solid ${theme.palette.background.paper}`
                                : "none",
                          }}
                        />
                      </Tooltip>
                    ))}
                  </Box>
                </Box>
              ),
            )}
          </Stack>
        )}

        {legend.length > 0 && (
          <Stack direction="row" flexWrap="wrap" sx={{ gap: 3 }}>
            {legend.map((entry) => (
              <Box
                key={entry.role}
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "2px",
                    backgroundColor: colors[entry.role],
                  }}
                />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ fontSize: "0.68rem" }}
                >
                  {legendText(entry)}
                </Typography>
              </Box>
            ))}
          </Stack>
        )}

        {notes.length > 0 && (
          <Stack spacing={0.5}>
            {notes.map((note) => (
              <Typography
                key={note.key}
                variant="caption"
                color="text.secondary"
                sx={{ fontSize: "0.68rem", lineHeight: 1.4 }}
              >
                {t(`experiments:splitPreview.notes.${note.key}`, note.values)}
              </Typography>
            ))}
          </Stack>
        )}
      </Stack>
    </SplitsCard>
  );
}

SplitPreview.propTypes = {
  preview: PropTypes.shape({
    rows: PropTypes.array.isRequired,
    notes: PropTypes.array.isRequired,
    shares: PropTypes.object.isRequired,
    legend: PropTypes.arrayOf(
      PropTypes.shape({
        role: PropTypes.string.isRequired,
        key: PropTypes.string.isRequired,
        values: PropTypes.object,
      }),
    ),
  }),
  loading: PropTypes.bool,
  // Why there is no preview: the backend's reason, and whether it refused the
  // parameters (a 422) rather than failing to compute the preview.
  failure: PropTypes.shape({
    reason: PropTypes.string,
    invalid: PropTypes.bool,
  }),
  onRetry: PropTypes.func,
  description: PropTypes.string,
  splitterDescription: PropTypes.string,
};

export default SplitPreview;
