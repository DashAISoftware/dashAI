import { useEffect, useState } from "react";
import {
  Box,
  CircularProgress,
  Collapse,
  Divider,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import DeleteIcon from "@mui/icons-material/Delete";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import StorageIcon from "@mui/icons-material/Storage";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getDatasetSources } from "../../api/hub";
import Footer from "../threeSectionLayout/Footer";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";

function SectionHeader({ icon: Icon, title, count, open, onToggle }) {
  const theme = useTheme();
  return (
    <Box
      display="flex"
      alignItems="center"
      sx={{
        cursor: "pointer",
        py: 0.5,
        px: 1,
        borderRadius: 1,
        "&:hover": { bgcolor: theme.palette.ui?.hover ?? theme.palette.action.hover },
      }}
      onClick={onToggle}
    >
      <Icon sx={{ fontSize: 20, color: theme.palette.primary.main, mr: 1 }} />
      <Typography
        variant="h5"
        sx={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          flex: 1,
        }}
        color="text.primary"
      >
        {title}
      </Typography>
      <Typography
        variant="body2"
        component="div"
        sx={{
          mr: 1,
          bgcolor: theme.palette.ui?.scrollbar ?? theme.palette.divider,
          color: theme.palette.text.primary,
          borderRadius: "50%",
          width: 20,
          height: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {count}
      </Typography>
      {open ? (
        <KeyboardArrowDownIcon
          sx={{ fontSize: 20, color: theme.palette.primary.main }}
        />
      ) : (
        <KeyboardArrowRightIcon
          sx={{ fontSize: 20, color: theme.palette.primary.main }}
        />
      )}
    </Box>
  );
}

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
  const { t } = useTranslation(["hub", "common"]);
  const theme = useTheme();
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sourcesOpen, setSourcesOpen] = useState(true);
  const [downloadsOpen, setDownloadsOpen] = useState(true);

  useEffect(() => {
    getDatasetSources()
      .then(setSources)
      .catch(() => setSources([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <SideBar>
      <Box sx={{ px: 2, py: 1.5, flexShrink: 0 }}>
        <Typography variant="body1" color="textSecondary">
          {t("hub:title")}
        </Typography>
      </Box>

      <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

      <Box
        display="flex"
        flexDirection="column"
        flex={1}
        minHeight={0}
        sx={{ overflowY: "auto" }}
      >
        {/* Sources section */}
        <Box sx={{ px: 2, pt: 2 }}>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", pt: 2 }}>
              <CircularProgress size={20} />
            </Box>
          ) : (
            <>
              <SectionHeader
                icon={CloudDownloadIcon}
                title={t("hub:sources")}
                count={sources.length}
                open={sourcesOpen}
                onToggle={() => setSourcesOpen((v) => !v)}
              />
              <Collapse in={sourcesOpen} timeout="auto">
                <Box pl={2}>
                  {sources.length === 0 ? (
                    <Typography
                      sx={{
                        color: "text.primary",
                        opacity: 0.5,
                        textAlign: "center",
                        p: 2,
                      }}
                    >
                      {t("common:noItemsAvailable", "No items available.")}
                    </Typography>
                  ) : (
                    sources.map((source) => (
                      <Box
                        key={source.name}
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          py: 0.75,
                          px: 1,
                          borderRadius: 1,
                          cursor: "pointer",
                          bgcolor:
                            selectedSource === source.name
                              ? theme.palette.action.selected
                              : "transparent",
                          borderLeft:
                            selectedSource === source.name
                              ? `3px solid ${theme.palette.primary.main}`
                              : "3px solid transparent",
                          "&:hover": {
                            bgcolor:
                              selectedSource === source.name
                                ? theme.palette.action.selected
                                : theme.palette.action.hover,
                          },
                        }}
                        onClick={() => onSelectSource(source)}
                      >
                        <Typography variant="body1" color="text.primary" noWrap>
                          {source.display_name || source.name}
                        </Typography>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          noWrap
                          sx={{ pl: 1 }}
                        >
                          {source.description}
                        </Typography>
                      </Box>
                    ))
                  )}
                </Box>
              </Collapse>
            </>
          )}
        </Box>

        <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto", my: 1 }} />

        {/* Downloads section */}
        <Box sx={{ px: 2, pb: 2 }}>
          <SectionHeader
            icon={StorageIcon}
            title={t("hub:downloadedDatasets")}
            count={downloads.length}
            open={downloadsOpen}
            onToggle={() => setDownloadsOpen((v) => !v)}
          />
          <Collapse in={downloadsOpen} timeout="auto">
            <Box pl={2}>
              {downloads.length === 0 ? (
                <Typography
                  sx={{
                    color: "text.primary",
                    opacity: 0.5,
                    textAlign: "center",
                    p: 2,
                  }}
                >
                  {t("common:noItemsAvailable", "No items available.")}
                </Typography>
              ) : (
                downloads.map((dl) => (
                  <Box
                    key={dl.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      width: "100%",
                      minHeight: "50px",
                      py: 0.5,
                      px: 1,
                      borderRadius: 1,
                    }}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="body1" color="text.primary" noWrap>
                        {dl.name}
                      </Typography>
                      <Typography
                        variant="body2"
                        noWrap
                        sx={{ pl: 1 }}
                        color={
                          dl.status === "error"
                            ? "error"
                            : dl.status === "ready"
                              ? "success.main"
                              : "text.secondary"
                        }
                      >
                        {t("hub:fromSource", { source: dl.source_name })}
                        {" · "}
                        {dl.status === "downloading"
                          ? t("hub:statusDownloading")
                          : dl.status === "error"
                            ? t("hub:statusError")
                            : t("hub:statusReady")}
                      </Typography>
                    </Box>
                    <Box sx={{ display: "flex", flexShrink: 0 }}>
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
                    </Box>
                  </Box>
                ))
              )}
            </Box>
          </Collapse>
        </Box>
      </Box>

      <Footer />
    </SideBar>
  );
}
