import { Box, Stack } from "@mui/material";
import { useTranslation } from "react-i18next";
import {
  MEDIA_KINDS,
  MEDIA_ORDER,
  parseCardinality,
  isActive,
  kindTooltip,
} from "./constants";
import { MediaKindButton } from "./MediaKindButton";

export function MediaOnlyPlaceholder({
  hasAnyMedia,
  inputsCardinality,
  filesByKind,
  onPick,
}) {
  const { t } = useTranslation(["generative"]);

  return (
    <Box
      sx={(theme) => ({
        flex: 1,
        minHeight: "104px",
        boxSizing: "border-box",
        px: 4,
        py: 3,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 2,
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 1,
        backgroundColor: "transparent",
        color: theme.palette.text.secondary,
      })}
    >
      {hasAnyMedia ? (
        <>
          <Box sx={{ fontSize: "0.875rem" }}>
            {t(
              "generative:label.attachMediaToContinue",
              "Attach media to continue",
            )}
          </Box>
          <Stack direction="row" spacing={2}>
            {MEDIA_ORDER.map((kind) => {
              const { icon, tooltipKey } = MEDIA_KINDS[kind];
              const enabled = isActive(inputsCardinality[kind]);
              const range = parseCardinality(inputsCardinality[kind]);
              const count = (filesByKind[kind] || []).length;
              const disabled = !enabled || (enabled && count >= range.max);
              const label = t(`generative:${tooltipKey}`, kind);
              return (
                <MediaKindButton
                  key={`inline-${kind}`}
                  icon={icon}
                  tooltip={kindTooltip(label, enabled, count, range)}
                  disabled={disabled}
                  onClick={() => onPick(kind)}
                />
              );
            })}
          </Stack>
        </>
      ) : (
        <Box sx={{ fontSize: "0.875rem" }}>
          {t(
            "generative:label.noInputAvailable",
            "No input available for this task",
          )}
        </Box>
      )}
    </Box>
  );
}
