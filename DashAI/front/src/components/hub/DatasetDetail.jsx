import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  Divider,
  Link,
  Stack,
  Typography,
} from "@mui/material";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import DownloadIcon from "@mui/icons-material/Download";
import AddIcon from "@mui/icons-material/Add";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getDatasetInfo, getDownloadUrl } from "../../api/hub";

/**
 * Right panel — detailed view of a selected Hub dataset with action buttons.
 *
 * @param {object|null} dataset - Selected DatasetEntry, or null if none.
 * @param {string|null} sourceName - Active DatasetSource class name.
 * @param {function} onStartImport - Called when user clicks "Add to DashAI".
 */
export default function DatasetDetail({ dataset, sourceName, onStartImport }) {
  const { t } = useTranslation(["hub"]);
  const theme = useTheme();
  const [extraInfo, setExtraInfo] = useState(null);

  useEffect(() => {
    if (!dataset || !sourceName) {
      setExtraInfo(null);
      return;
    }
    setExtraInfo(null);
    getDatasetInfo(sourceName, dataset.id)
      .then((info) => setExtraInfo(info))
      .catch(() => setExtraInfo({}));
  }, [dataset?.id, sourceName]);

  if (!dataset) {
    return (
      <Box
        sx={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 3,
          bgcolor: "background.box",
        }}
      >
        <Typography variant="body2" color="text.secondary" textAlign="center">
          {t("hub:selectDatasetToPreview")}
        </Typography>
      </Box>
    );
  }

  const handleDownload = async () => {
    try {
      const url = await getDownloadUrl(sourceName, dataset.id);
      window.location.href = url;
    } catch {
      // silently fail — source page link is still available
    }
  };

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.box",
        overflowY: "auto",
      }}
    >
      <Box
        sx={{
          p: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          flexShrink: 0,
        }}
      >
        <Typography variant="h6" fontWeight={600} gutterBottom>
          {dataset.name}
        </Typography>

        <Stack direction="row" spacing={1} mb={1.5}>
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => onStartImport?.()}
          >
            {t("hub:addToDashAI")}
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
          >
            {t("hub:download")}
          </Button>
        </Stack>

        <Link
          href={dataset.url}
          target="_blank"
          rel="noopener noreferrer"
          variant="caption"
          sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
        >
          {t("hub:viewOnSource")} <OpenInNewIcon sx={{ fontSize: 12 }} />
        </Link>
      </Box>

      <Box sx={{ p: 2, flex: 1 }}>
        {(extraInfo?.description || dataset.description) && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {extraInfo?.description || dataset.description}
          </Typography>
        )}

        <Divider sx={{ mb: 1.5 }} />

        <Stack spacing={1}>
          {dataset.row_count != null && (
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("hub:rows")}
              </Typography>
              <Typography variant="body2">
                {dataset.row_count.toLocaleString()}
              </Typography>
            </Box>
          )}

          {(extraInfo?.tags ?? dataset.tags)?.length > 0 && (
            <Box>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                mb={0.5}
              >
                {t("hub:tags")}
              </Typography>
              <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap>
                {(extraInfo?.tags ?? dataset.tags).map((tag) => (
                  <Chip key={tag} label={tag} size="small" variant="outlined" />
                ))}
              </Stack>
            </Box>
          )}
        </Stack>
      </Box>
    </Box>
  );
}
