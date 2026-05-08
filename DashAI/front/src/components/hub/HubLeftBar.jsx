import { useEffect, useState } from "react";
import {
  Box,
  CircularProgress,
  Divider,
  IconButton,
  List,
  ListItemButton,
  ListItemSecondaryAction,
  ListItemText,
  Tooltip,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getDatasetSources } from "../../api/hub";

/**
 * Left sidebar for the Hub module.
 *
 * @param {string|null} selectedSource - Currently active source name.
 * @param {function} onSelectSource - Called with full source object when user clicks.
 * @param {Array} downloads - List of HubDownload records to show.
 * @param {function} onDeleteDownload - Called with download id when user deletes.
 * @param {function} onImportDownload - Called with download record when user clicks Add.
 */
export default function HubLeftBar({
  selectedSource,
  onSelectSource,
  downloads = [],
  onDeleteDownload,
  onImportDownload,
}) {
  const { t } = useTranslation(["hub"]);
  const theme = useTheme();
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDatasetSources()
      .then(setSources)
      .catch(() => setSources([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.box",
        borderRight: `1px solid ${theme.palette.divider}`,
        overflowY: "auto",
      }}
    >
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: `1px solid ${theme.palette.divider}`,
          flexShrink: 0,
        }}
      >
        <Typography variant="subtitle2" color="text.secondary">
          {t("hub:title")}
        </Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", pt: 4 }}>
          <CircularProgress size={24} />
        </Box>
      ) : (
        <List disablePadding>
          {sources.map((source) => (
            <ListItemButton
              key={source.name}
              selected={selectedSource === source.name}
              onClick={() => onSelectSource(source)}
              sx={{
                "&.Mui-selected": {
                  bgcolor: "action.selected",
                  borderLeft: `3px solid ${theme.palette.primary.main}`,
                },
                "&.Mui-selected:hover": { bgcolor: "action.selected" },
              }}
            >
              <ListItemText
                primary={source.display_name || source.name}
                secondary={source.description}
                secondaryTypographyProps={{
                  noWrap: true,
                  variant: "caption",
                }}
              />
            </ListItemButton>
          ))}
        </List>
      )}

      {downloads.length > 0 && (
        <>
          <Divider />
          <Box
            sx={{
              px: 2,
              py: 1,
              flexShrink: 0,
            }}
          >
            <Typography variant="subtitle2" color="text.secondary">
              {t("hub:downloadedDatasets")}
            </Typography>
          </Box>
          <List disablePadding>
            {downloads.map((dl) => (
              <ListItemButton key={dl.id} disableRipple sx={{ pr: 9 }}>
                <ListItemText
                  primary={dl.name}
                  secondary={
                    dl.status === "downloading"
                      ? t("hub:statusDownloading")
                      : dl.status === "error"
                        ? t("hub:statusError")
                        : t("hub:statusReady")
                  }
                  secondaryTypographyProps={{
                    noWrap: true,
                    variant: "caption",
                    color:
                      dl.status === "error"
                        ? "error"
                        : dl.status === "ready"
                          ? "success.main"
                          : "text.secondary",
                  }}
                />
                <ListItemSecondaryAction>
                  {dl.status === "ready" && (
                    <Tooltip title={t("hub:addToDashAI")}>
                      <IconButton
                        size="small"
                        onClick={() => onImportDownload?.(dl)}
                      >
                        <AddIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                  <Tooltip title={t("common:delete")}>
                    <IconButton
                      size="small"
                      onClick={() => onDeleteDownload?.(dl.id)}
                      disabled={dl.status === "downloading"}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </ListItemSecondaryAction>
              </ListItemButton>
            ))}
          </List>
        </>
      )}
    </Box>
  );
}
