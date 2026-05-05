import { useEffect, useState } from "react";
import {
  Box,
  CircularProgress,
  List,
  ListItemButton,
  ListItemText,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getDatasetSources } from "../../api/hub";

/**
 * Left sidebar for the Hub module — lists available DatasetSource components.
 *
 * @param {string|null} selectedSource - Currently active source name.
 * @param {function} onSelectSource - Called with source name when user clicks.
 */
export default function HubLeftBar({ selectedSource, onSelectSource }) {
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
        <List disablePadding sx={{ flex: 1, overflowY: "auto" }}>
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
    </Box>
  );
}
