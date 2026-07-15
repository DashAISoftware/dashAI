import React, { useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  IconButton,
  Menu,
  MenuItem,
  Typography,
  Tooltip,
  Dialog,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import EditIcon from "@mui/icons-material/Edit";
import FullscreenIcon from "@mui/icons-material/Fullscreen";
import SaveIcon from "@mui/icons-material/Save";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import CloseIcon from "@mui/icons-material/Close";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import { useTheme, alpha } from "@mui/material/styles";
import Plot from "react-plotly.js";
import { useTranslation } from "react-i18next";

import ArtifactRenderer from "./ArtifactRenderer";
import { applyThemeToLayout } from "../../utils/plotlyTheme";
import { downloadArtifact } from "../../utils/downloadArtifact";

/**
 * Renders one typed artifact as a self contained bordered block. The actions
 * that apply to that artifact (download, plot editing, fullscreen) live in a
 * compact cluster docked to the block's top right corner, revealed on hover
 * or keyboard focus so the resting card stays uncluttered. Plot editing is
 * offered only for plotly artifacts; edits persist when onSaveEdit is given,
 * otherwise they are client side only.
 */
export default function ArtifactViewer({
  artifact,
  onSaveEdit = null,
  onResetEdit = null,
  canReset = false,
  siblingArtifacts = null,
  siblingIndex = 0,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["explainers", "common"]);
  const [downloadAnchor, setDownloadAnchor] = useState(null);
  const [editing, setEditing] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenIndex, setFullscreenIndex] = useState(siblingIndex);
  const hasSiblings = siblingArtifacts && siblingArtifacts.length > 1;
  const fullscreenArtifact = hasSiblings
    ? siblingArtifacts[fullscreenIndex]
    : artifact;

  const openFullscreen = () => {
    setFullscreenIndex(siblingIndex);
    setFullscreen(true);
  };

  const stepFullscreen = (delta) => {
    if (!hasSiblings) return;
    setFullscreenIndex(
      (fullscreenIndex + delta + siblingArtifacts.length) %
        siblingArtifacts.length,
    );
  };
  // editInitial is the figure the editable Plot mounts with (set once per edit
  // session). editFigureRef holds the latest edited figure, captured in
  // onUpdate WITHOUT setState so Plotly's own edit events do not trigger a
  // React re render that would re run Plotly.react and loop the page into a
  // freeze.
  const [editInitial, setEditInitial] = useState(null);
  const editFigureRef = useRef(null);
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

  const startEdit = () => {
    if (!figure?.data) return;
    const initial = {
      data: JSON.parse(JSON.stringify(figure.data)),
      layout: applyThemeToLayout(figure.layout, theme),
    };
    setEditInitial(initial);
    editFigureRef.current = initial;
    setEditing(true);
  };

  const closeEdit = () => {
    setEditing(false);
    setEditInitial(null);
    editFigureRef.current = null;
  };

  const saveEdit = async () => {
    try {
      if (onSaveEdit && editFigureRef.current) {
        await onSaveEdit(editFigureRef.current);
      }
      closeEdit();
    } catch (error) {
      console.error("Failed to save plot edits", error);
    }
  };

  const findPlotEl = () =>
    plotWrapRef.current
      ? plotWrapRef.current.querySelector(".js-plotly-plot")
      : null;

  const actionButtonSx = {
    color: "text.secondary",
    "&:hover": { color: "text.primary" },
  };

  // Circular "glass" buttons for the fullscreen lightbox: translucent white
  // against the dark blurred overlay, regardless of the app's light/dark
  // theme (the overlay itself is always near black).
  const lightboxButtonSx = {
    position: "absolute",
    top: 16,
    right: 16,
    zIndex: 1,
    width: 36,
    height: 36,
    color: "#fff",
    bgcolor: "rgba(255, 255, 255, 0.12)",
    border: "1px solid rgba(255, 255, 255, 0.2)",
    "&:hover": { bgcolor: "rgba(255, 255, 255, 0.25)" },
  };

  const lightboxArrowSx = {
    top: "50%",
    right: "auto",
    transform: "translateY(-50%)",
    width: 44,
    height: 44,
  };

  // Fill most of the viewport in the fullscreen view, leaving room for the
  // header bar and padding.
  const fullscreenHeight =
    typeof window !== "undefined"
      ? Math.max(360, Math.round(window.innerHeight * 0.8))
      : 720;

  return (
    <Box
      ref={plotWrapRef}
      sx={{
        position: "relative",
        width: "100%",
        border: `1px solid ${theme.palette.ui.border}`,
        borderRadius: 1,
        bgcolor: theme.palette.ui.box,
        p: 3,
        "& .artifact-actions": {
          opacity: 0,
          transition: "opacity 0.15s ease",
        },
        "&:hover .artifact-actions, &:focus-within .artifact-actions": {
          opacity: 1,
        },
        "@media (hover: none)": {
          "& .artifact-actions": { opacity: 1 },
        },
      }}
    >
      {/* Action cluster, docked to the block corner and attached to this
          artifact's content. */}
      <Box
        className="artifact-actions"
        sx={{
          position: "absolute",
          top: 6,
          right: 6,
          zIndex: 3,
          display: "flex",
          gap: 0.5,
          p: 0.5,
          borderRadius: 1,
          bgcolor: alpha(theme.palette.background.paper, 0.85),
          backdropFilter: "blur(4px)",
          border: `1px solid ${theme.palette.ui.border}`,
        }}
      >
        <Tooltip title={t("explainers:button.download")}>
          <IconButton
            size="small"
            sx={actionButtonSx}
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
            <IconButton size="small" sx={actionButtonSx} onClick={startEdit}>
              <EditIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        {canReset && onResetEdit && (
          <Tooltip title={t("explainers:button.resetPlot")}>
            <IconButton size="small" sx={actionButtonSx} onClick={onResetEdit}>
              <RestartAltIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
        <Tooltip title={t("explainers:button.fullscreen")}>
          <IconButton size="small" sx={actionButtonSx} onClick={openFullscreen}>
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

      {/* The instance label is shown once by the parent; suppress the
          per artifact title so it is not repeated on every block. */}
      <ArtifactRenderer artifact={{ ...artifact, title: null }} />

      {/* Edit dialog: editable plotly figure. The Plot mounts once with
          editInitial and reports edits through onUpdate into a ref; we never
          feed those edits back as props, so Plotly does not re render in a
          loop. */}
      <Dialog open={editing} onClose={closeEdit} fullWidth maxWidth="lg">
        <Box sx={{ display: "flex", justifyContent: "flex-end", p: 1, gap: 1 }}>
          {onSaveEdit && (
            <Tooltip title={t("common:save")}>
              <IconButton onClick={saveEdit}>
                <SaveIcon />
              </IconButton>
            </Tooltip>
          )}
          <IconButton onClick={closeEdit}>
            <CloseIcon />
          </IconButton>
        </Box>
        {editInitial && (
          <Plot
            data={editInitial.data}
            layout={{ ...editInitial.layout, autosize: true, height: 500 }}
            config={{ editable: true, displaylogo: false, responsive: true }}
            onUpdate={(fig) => {
              editFigureRef.current = { data: fig.data, layout: fig.layout };
            }}
            useResizeHandler
            style={{ width: "100%" }}
          />
        )}
      </Dialog>

      {/* Fullscreen view: dark blurred lightbox overlay, rounded/shadowed
          content card, and circular glass buttons for close + prev/next. */}
      <Dialog
        open={fullscreen}
        fullScreen
        onClose={() => setFullscreen(false)}
        transitionDuration={0}
        keepMounted
        PaperProps={{
          elevation: 0,
          sx: {
            bgcolor: "rgba(0, 0, 0, 0.15)",
            backgroundImage: "none",
            backdropFilter: "blur(6px)",
            willChange: "backdrop-filter",
            boxShadow: "none",
          },
        }}
      >
        <Box
          onClick={(e) => {
            if (e.target === e.currentTarget) setFullscreen(false);
          }}
          sx={{
            position: "relative",
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <IconButton
            onClick={() => setFullscreen(false)}
            aria-label={t("explainers:button.close", {
              defaultValue: "Close",
            })}
            sx={lightboxButtonSx}
          >
            <CloseIcon sx={{ fontSize: 18 }} />
          </IconButton>

          {hasSiblings && (
            <IconButton
              onClick={() => stepFullscreen(-1)}
              aria-label="previous"
              sx={{ ...lightboxButtonSx, ...lightboxArrowSx, left: 20 }}
            >
              <ArrowBackIosNewIcon sx={{ fontSize: 22 }} />
            </IconButton>
          )}

          <Box
            sx={{
              width: "90vw",
              maxWidth: 1100,
              maxHeight: "90vh",
              overflow: "auto",
              bgcolor: "background.paper",
              borderRadius: "10px",
              boxShadow: "0 30px 80px rgba(0, 0, 0, 0.6)",
              p: 4,
            }}
          >
            <ArtifactRenderer
              artifact={{ ...fullscreenArtifact, title: null }}
              height={fullscreenHeight}
            />
          </Box>

          {hasSiblings && (
            <IconButton
              onClick={() => stepFullscreen(1)}
              aria-label="next"
              sx={{ ...lightboxButtonSx, ...lightboxArrowSx, right: 20 }}
            >
              <ArrowForwardIosIcon sx={{ fontSize: 22 }} />
            </IconButton>
          )}
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
  siblingArtifacts: PropTypes.array,
  siblingIndex: PropTypes.number,
};
