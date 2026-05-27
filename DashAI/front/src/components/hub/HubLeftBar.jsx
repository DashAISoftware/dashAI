import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import StorageIcon from "@mui/icons-material/Storage";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import Footer from "../threeSectionLayout/Footer";
import SearchBar from "../threeSectionLayout/SearchBar";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { useDatasets } from "../../hooks/datasets/useDatasets";

function SectionHeader({ icon: Icon, title, count, open, onToggle }) {
  const theme = useTheme();
  return (
    <Box
      display="flex"
      alignItems="center"
      sx={{
        cursor: "pointer",
        py: 2,
        px: 4,
        borderRadius: 1,
        "&:hover": {
          bgcolor: theme.palette.ui?.hover ?? theme.palette.action.hover,
        },
      }}
      onClick={onToggle}
    >
      <Icon sx={{ fontSize: 20, color: theme.palette.primary.main, mr: 4 }} />
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
          mr: 4,
          bgcolor: "primary.main",
          color: "primary.contrastText",
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
 * Left sidebar for the Hub module — shows DashAI datasets and downloaded datafiles.
 *
 * @param {Array} downloads - List of Datafile records to show.
 * @param {function} onDeleteDownload - Called with download id when user deletes.
 * @param {function} onImportDownload - Called with download record when user clicks Add.
 */
export default function HubLeftBar({
  downloads = [],
  onDeleteDownload,
  onImportDownload,
}) {
  const { t } = useTranslation(["hub", "common", "datasets"]);
  const theme = useTheme();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [datasetsOpen, setDatasetsOpen] = useState(true);
  const [downloadsOpen, setDownloadsOpen] = useState(true);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);
  const { datasets } = useDatasets({ t });

  const q = searchQuery.toLowerCase();
  const filteredDatasets = datasets.filter((d) =>
    d.name.toLowerCase().includes(q),
  );
  const filteredDownloads = downloads.filter((dl) =>
    dl.name.toLowerCase().includes(q),
  );

  const handleDeleteConfirm = () => {
    onDeleteDownload?.(pendingDeleteId);
    setPendingDeleteId(null);
  };

  return (
    <SideBar>
      <Box
        sx={{
          p: 4,
          height: "64px",
          display: "flex",
          alignItems: "center",
          flexShrink: 0,
        }}
      >
        <Typography variant="body1" color="textSecondary">
          {t("hub:title")}
        </Typography>
      </Box>

      <Box px={4} pb={4} sx={{ flexShrink: 0 }}>
        <SearchBar
          placeholder={t("hub:searchDownloads", "Search...")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </Box>

      <Divider sx={{ width: "90%", bgcolor: "divider", mx: "auto" }} />

      <Box display="flex" flexDirection="column" flex={1} minHeight={0}>
        {/* Datasets — top half */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box sx={{ pl: 4, pr: 4, pt: 4, flexShrink: 0 }}>
            <SectionHeader
              icon={StorageIcon}
              title={t("datasets:label.availableDatasets")}
              count={filteredDatasets.length}
              open={datasetsOpen}
              onToggle={() => setDatasetsOpen((v) => !v)}
            />
          </Box>
          <Collapse
            in={datasetsOpen}
            timeout="auto"
            sx={{ flex: 1, minHeight: 0, overflow: "auto" }}
          >
            <Box pl={4} pr={4} pb={4}>
              {filteredDatasets.length === 0 ? (
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
                filteredDatasets.map((ds) => (
                  <Box
                    key={ds.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      width: "100%",
                      height: "50px",
                      p: 1,
                      borderRadius: 1,
                      cursor: "pointer",
                      "&:hover": { bgcolor: theme.palette.action.hover },
                    }}
                    onClick={() => navigate(`/app/data/datasets/${ds.id}`)}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="body1" color="text.primary" noWrap>
                        {ds.name}
                      </Typography>
                      <Typography
                        variant="body2"
                        noWrap
                        sx={{ pl: 1 }}
                        color="text.secondary"
                      >
                        {ds.total_rows} {t("common:rows")}, {ds.total_columns}{" "}
                        {t("common:columns")}
                      </Typography>
                    </Box>
                  </Box>
                ))
              )}
            </Box>
          </Collapse>
        </Box>

        <Divider
          sx={{ width: "90%", bgcolor: "divider", mx: "auto", flexShrink: 0 }}
        />

        {/* Datafiles — bottom half */}
        <Box
          sx={{
            flex: 1,
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box sx={{ pl: 4, pr: 4, pt: 4, flexShrink: 0 }}>
            <SectionHeader
              icon={CloudDownloadIcon}
              title={t("hub:downloadedDatasets")}
              count={filteredDownloads.length}
              open={downloadsOpen}
              onToggle={() => setDownloadsOpen((v) => !v)}
            />
          </Box>
          <Collapse
            in={downloadsOpen}
            timeout="auto"
            sx={{ flex: 1, minHeight: 0, overflow: "auto" }}
          >
            <Box pl={4} pr={4} pb={4}>
              {filteredDownloads.length === 0 ? (
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
                filteredDownloads.map((dl) => (
                  <Box
                    key={dl.id}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      width: "100%",
                      height: "50px",
                      p: 1,
                      borderRadius: 1,
                      cursor: dl.status === "ready" ? "pointer" : "default",
                      "&:hover":
                        dl.status === "ready"
                          ? { bgcolor: theme.palette.action.hover }
                          : {},
                    }}
                    onClick={() =>
                      dl.status === "ready" && onImportDownload?.(dl)
                    }
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="body1" color="text.primary" noWrap>
                        {dl.name}
                      </Typography>
                      <Typography
                        variant="body2"
                        noWrap
                        sx={{ pl: 1 }}
                        color="text.secondary"
                      >
                        {t("hub:fromSource", { source: dl.source_name })}
                      </Typography>
                    </Box>
                    <Box sx={{ display: "flex", flexShrink: 0 }}>
                      <Tooltip title={t("common:delete")}>
                        <span>
                          <IconButton
                            size="small"
                            color={
                              dl.status === "downloading" ? "default" : "error"
                            }
                            onClick={(e) => {
                              e.stopPropagation();
                              setPendingDeleteId(dl.id);
                            }}
                            disabled={dl.status === "downloading"}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </span>
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

      <Dialog
        open={pendingDeleteId !== null}
        onClose={() => setPendingDeleteId(null)}
      >
        <DialogTitle>{t("common:confirmDeletion")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t("common:confirmDeletionMessage")}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDeleteId(null)} color="text.primary">
            {t("common:cancel")}
          </Button>
          <Button color="error" onClick={handleDeleteConfirm}>
            {t("common:delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </SideBar>
  );
}
