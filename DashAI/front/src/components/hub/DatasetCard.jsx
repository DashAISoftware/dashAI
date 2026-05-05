import { Box, Chip, Paper, Stack, Typography } from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import { useTranslation } from "react-i18next";

/**
 * Card displaying a single dataset from the Hub.
 *
 * @param {object} dataset - DatasetEntry object.
 * @param {boolean} selected - Whether this card is currently selected.
 * @param {function} onSelect - Called when the card is clicked.
 */
export default function DatasetCard({ dataset, selected, onSelect }) {
  const { t } = useTranslation(["hub"]);

  const formatSize = (bytes) => {
    if (!bytes) return null;
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
    return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  };

  return (
    <Paper
      elevation={0}
      onClick={onSelect}
      sx={{
        p: 1.5,
        cursor: "pointer",
        border: 1,
        borderColor: selected ? "primary.main" : "divider",
        bgcolor: selected ? "action.selected" : "background.paper",
        transition: "border-color 0.15s, background 0.15s",
        "&:hover": { borderColor: "primary.light" },
        display: "flex",
        flexDirection: "column",
        gap: 0.75,
      }}
    >
      <Typography variant="subtitle2" fontWeight={600} noWrap>
        {dataset.name}
      </Typography>

      {dataset.description && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
        >
          {dataset.description}
        </Typography>
      )}

      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
        {dataset.tags?.slice(0, 3).map((tag) => (
          <Chip key={tag} label={tag} size="small" variant="outlined" />
        ))}
      </Stack>

      <Stack direction="row" spacing={1} alignItems="center">
        <StorageIcon sx={{ fontSize: 14, color: "text.disabled" }} />
        <Typography variant="caption" color="text.disabled">
          {dataset.row_count
            ? `${dataset.row_count.toLocaleString()} ${t("hub:rows")}`
            : "—"}
          {dataset.size_bytes ? ` · ${formatSize(dataset.size_bytes)}` : ""}
        </Typography>
      </Stack>
    </Paper>
  );
}
