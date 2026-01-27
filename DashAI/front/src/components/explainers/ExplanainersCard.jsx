import React, { useState, useEffect } from "react";
import {
  Grid,
  Typography,
  IconButton,
  Paper,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Collapse,
  Box,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import PropTypes from "prop-types";
import ExplainersPlot from "./ExplainersPlot";
import { useNavigate } from "react-router-dom";
import { deleteExplainer } from "../../api/explainer";
import { useTranslation } from "react-i18next";
import { getComponentById } from "../../api/component";

/**
 * GlobalExplainersCard
 * @param {*} explainer
 * @returns Component that render a card for the explainer
 */
export default function ExplainersCard({
  explainer,
  scope,
  onDelete,
  compact = false,
}) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(() => {
    const saved = localStorage.getItem(`explainer-${explainer.id}-expanded`);
    return saved !== null ? JSON.parse(saved) : true;
  });

  useEffect(() => {
    localStorage.setItem(
      `explainer-${explainer.id}-expanded`,
      JSON.stringify(expanded),
    );
  }, [expanded, explainer.id]);
  const [componentData, setComponentData] = useState(null);
  const { t } = useTranslation(["explainers"]);

  function plotName(name) {
    return name.match(/[A-Z][a-z]+|[0-9]+/g).join(" ");
  }

  const navigate = useNavigate();

  const handleDeleteExplainer = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const handleConfirmDelete = async () => {
    await deleteExplainer(scope, explainer.id);
    handleClose();
    if (onDelete) {
      onDelete();
    } else {
      window.location.reload();
    }
  };

  useEffect(() => {
    getComponentById(explainer.explainer_name)
      .then((data) => {
        setComponentData(data);
      })
      .catch((error) => {
        console.error("Error fetching component data:", error);
      });
  }, [explainer.explainer_name]);

  if (compact) {
    return (
      <>
        <Paper elevation={2} sx={{ p: 2, width: "100%" }}>
          <Grid container direction="column" gap={1}>
            <Grid
              item
              container
              direction="row"
              justifyContent="space-between"
              alignItems="center"
            >
              <Grid item>
                <Typography
                  variant="subtitle2"
                  fontWeight="medium"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    flexWrap: "wrap",
                  }}
                >
                  {componentData
                    ? componentData.display_name
                    : plotName(explainer.explainer_name)}
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    component="span"
                  >
                    {explainer.name}
                  </Typography>
                </Typography>
              </Grid>
              <Grid item>
                <IconButton
                  size="small"
                  aria-label="delete"
                  color="error"
                  onClick={handleDeleteExplainer}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Grid>
            </Grid>

            {/* Expandable plot section */}
            <Grid item>
              <Button
                size="small"
                onClick={() => setExpanded(!expanded)}
                endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                sx={{ textTransform: "none" }}
              >
                {expanded
                  ? t("explainers:button.hidePlot")
                  : t("explainers:button.showPlot")}
              </Button>

              <Collapse in={expanded} timeout="auto" unmountOnExit>
                <Box sx={{ mt: 2 }}>
                  <ExplainersPlot explainer={explainer} scope={scope} />
                </Box>
              </Collapse>
            </Grid>
          </Grid>
        </Paper>

        <Dialog
          open={open}
          onClose={handleClose}
          aria-labelledby="alert-dialog-title"
          aria-describedby="alert-dialog-description"
        >
          <DialogTitle id="alert-dialog-title">
            {t("explainers:label.deleteExplainer")}
          </DialogTitle>
          <DialogContent>
            <DialogContentText id="alert-dialog-description">
              {t("explainers:label.deleteExplainerConfirmation")}
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose}>{t("common:cancel")}</Button>
            <Button onClick={handleConfirmDelete} color="error" autoFocus>
              {t("common:delete")}
            </Button>
          </DialogActions>
        </Dialog>
      </>
    );
  }

  // Full mode for standalone page
  return (
    <Paper elevation={3}>
      <Grid container item minWidth={800} maxWidth={800} p={4} gap={2}>
        <Grid
          item
          container
          direction={"row"}
          justifyContent={"space-between"}
          alignItems={"center"}
        >
          <Grid>
            <Typography variant="h6">
              {plotName(explainer.explainer_name)}
            </Typography>
            <Typography variant="h7">
              {t("explainers:label.forExplainer", { name: explainer.name })}
            </Typography>
          </Grid>
          <Grid>
            <IconButton
              aria-label="zoomin"
              onClick={() => {
                navigate(
                  `/app/explainers/explainer/${scope}/${explainer.run_id}/${explainer.id}`,
                );
              }}
            >
              <ZoomInIcon />
            </IconButton>
            <IconButton
              aria-label="delete"
              color="error"
              onClick={handleDeleteExplainer}
            >
              <DeleteIcon />
            </IconButton>
            <Dialog
              open={open}
              onClose={handleClose}
              aria-labelledby="alert-dialog-title"
              aria-describedby="alert-dialog-description"
            >
              <DialogTitle id="alert-dialog-title">
                {t("explainers:label.deleteExplainer")}
              </DialogTitle>
              <DialogContent>
                <DialogContentText id="alert-dialog-description">
                  {t("explainers:label.deleteExplainerConfirmation")}
                </DialogContentText>
              </DialogContent>
              <DialogActions>
                <Button onClick={handleClose}>{t("common:cancel")}</Button>
                <Button onClick={handleConfirmDelete} color="error" autoFocus>
                  {t("common:delete")}
                </Button>
              </DialogActions>
            </Dialog>
          </Grid>
        </Grid>
        <ExplainersPlot explainer={explainer} scope={scope} />
      </Grid>
    </Paper>
  );
}

ExplainersCard.propTypes = {
  explainer: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    run_id: PropTypes.number,
    explainer_name: PropTypes.string,
    explanation_path: PropTypes.string,
    plot_path: PropTypes.string,
    parameters: PropTypes.objectOf(
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
        PropTypes.arrayOf(PropTypes.string),
      ]),
    ),
    created: PropTypes.string,
    status: PropTypes.number,
  }).isRequired,
  scope: PropTypes.string.isRequired,
  onDelete: PropTypes.func,
  compact: PropTypes.bool,
};
