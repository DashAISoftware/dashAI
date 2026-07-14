// DashAI/front/src/components/shared/ArtifactViewer.jsx
import React, { useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  IconButton,
  Menu,
  MenuItem,
  Tooltip,
  Dialog,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import EditIcon from "@mui/icons-material/Edit";
import FullscreenIcon from "@mui/icons-material/Fullscreen";
import SaveIcon from "@mui/icons-material/Save";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import CloseIcon from "@mui/icons-material/Close";
import { useTheme } from "@mui/material/styles";
import Plot from "react-plotly.js";
import { useTranslation } from "react-i18next";

import ArtifactRenderer from "./ArtifactRenderer";
import { applyThemeToLayout } from "../../utils/plotlyTheme";
import { downloadArtifact } from "../../utils/downloadArtifact";

/**
 * Renders a single typed artifact with a toolbar: type-aware download, plot
 * editing (plotly only), and fullscreen. When onSaveEdit is provided, edited
 * plotly figures can be persisted; otherwise edits are client-side only.
 */
export default function ArtifactViewer({
  artifact,
  onSaveEdit = null,
  onResetEdit = null,
  canReset = false,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["explainers", "common"]);
  const [downloadAnchor, setDownloadAnchor] = useState(null);
  const [editing, setEditing] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const plotWrapRef = useRef(null);
  const isPlotly = artifact.type === "plotly";

  const figure = useMemo(() => {
    if (!isPlotly) return null;
    try {
      return typeof artifact.payload === "string"
        ? JSON.parse(artifact.payload)
        : artifact.payload;
    } catch (error) {
      console.error("Invalid plotly payload", error);
      return null;
    }
  }, [artifact, isPlotly]);

  const [editFigure, setEditFigure] = useState(null);

  const startEdit = () => {
    setEditFigure({
      data: JSON.parse(JSON.stringify(figure.data)),
      layout: applyThemeToLayout(figure.layout, theme),
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    if (onSaveEdit && editFigure) await onSaveEdit(editFigure);
    setEditing(false);
  };

  const findPlotEl = () =>
    plotWrapRef.current
      ? plotWrapRef.current.querySelector(".js-plotly-plot")
      : null;

  return (
    <Box sx={{ width: "100%", position: "relative" }} ref={plotWrapRef}>
      {/* Toolbar */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "flex-end",
          gap: 1,
          mb: 1,
        }}
      >
        <Tooltip title={t("explainers:button.download")}>
          <IconButton
            size="small"
            onClick={(e) =>
              isPlotly
                ? setDownloadAnchor(e.currentTarget)
                : downloadArtifact(artifact)
            }
          >
            <DownloadIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        {isPlotly && figure && (
          <Tooltip title={t("explainers:button.editPlot")}>
            <IconButton size="small" onClick={startEdit}>
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        {canReset && onResetEdit && (
          <Tooltip title={t("explainers:button.resetPlot")}>
            <IconButton size="small" onClick={onResetEdit}>
              <RestartAltIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        <Tooltip title={t("explainers:button.fullscreen")}>
          <IconButton size="small" onClick={() => setFullscreen(true)}>
            <FullscreenIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Menu
        anchorEl={downloadAnchor}
        open={Boolean(downloadAnchor)}
        onClose={() => setDownloadAnchor(null)}
      >
        <MenuItem
          onClick={() => {
            downloadArtifact(artifact, { plotEl: findPlotEl(), format: "png" });
            setDownloadAnchor(null);
          }}
        >
          {t("explainers:button.downloadPng")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            downloadArtifact(artifact, { plotEl: findPlotEl(), format: "svg" });
            setDownloadAnchor(null);
          }}
        >
          {t("explainers:button.downloadSvg")}
        </MenuItem>
      </Menu>

      <ArtifactRenderer artifact={artifact} />

      {/* Edit dialog: editable plotly figure */}
      <Dialog
        open={editing}
        onClose={() => setEditing(false)}
        fullWidth
        maxWidth="lg"
      >
        <Box sx={{ display: "flex", justifyContent: "flex-end", p: 1, gap: 1 }}>
          {onSaveEdit && (
            <Tooltip title={t("common:save")}>
              <IconButton onClick={saveEdit}>
                <SaveIcon />
              </IconButton>
            </Tooltip>
          )}
          <IconButton onClick={() => setEditing(false)}>
            <CloseIcon />
          </IconButton>
        </Box>
        {editFigure && (
          <Plot
            data={editFigure.data}
            layout={{ ...editFigure.layout, autosize: true, height: 500 }}
            config={{ editable: true, displaylogo: false, responsive: true }}
            onUpdate={(fig) =>
              setEditFigure({ data: fig.data, layout: fig.layout })
            }
            useResizeHandler
            style={{ width: "100%" }}
          />
        )}
      </Dialog>

      {/* Fullscreen view */}
      <Dialog open={fullscreen} fullScreen onClose={() => setFullscreen(false)}>
        <Box sx={{ display: "flex", justifyContent: "flex-end", p: 1 }}>
          <IconButton onClick={() => setFullscreen(false)}>
            <CloseIcon />
          </IconButton>
        </Box>
        <Box sx={{ p: 2 }}>
          <ArtifactRenderer artifact={artifact} />
        </Box>
      </Dialog>
    </Box>
  );
}

ArtifactViewer.propTypes = {
  artifact: PropTypes.shape({
    type: PropTypes.string.isRequired,
    payload: PropTypes.any,
    title: PropTypes.string,
    role: PropTypes.string,
  }).isRequired,
  onSaveEdit: PropTypes.func,
  onResetEdit: PropTypes.func,
  canReset: PropTypes.bool,
};
