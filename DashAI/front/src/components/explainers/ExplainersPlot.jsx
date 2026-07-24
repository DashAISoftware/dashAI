import { React, useEffect, useState } from "react";
import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  CircularProgress,
  Box,
  Typography,
} from "@mui/material";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";

import { getExplainerPlot as getExplainerPlotRequest } from "../../api/explainer";
import { useTranslation } from "react-i18next";
import ArtifactRenderer from "../shared/ArtifactRenderer";

/**
 * Coerce the plot endpoint response into a list of typed artifacts.
 * Legacy responses are lists of plotly JSON strings; they are wrapped as
 * plotly artifacts. Typed dicts pass through untouched.
 */
function parseExplanationArtifacts(items) {
  return items.map((item) =>
    typeof item === "string"
      ? { type: "plotly", payload: item, title: null }
      : item,
  );
}

/**
 * Group consecutive artifacts sharing the same non null title. Explainers
 * emit several artifacts per explained instance (e.g. a plot followed by a
 * text summary) under one title; each group becomes a single entry in the
 * instance selector and its artifacts render stacked together. Untitled
 * artifacts stay in their own group.
 */
function groupArtifacts(artifacts) {
  const groups = [];
  artifacts.forEach((artifact) => {
    const lastGroup = groups[groups.length - 1];
    if (
      artifact.title != null &&
      lastGroup &&
      lastGroup.title === artifact.title
    ) {
      lastGroup.artifacts.push(artifact);
    } else {
      groups.push({ title: artifact.title ?? null, artifacts: [artifact] });
    }
  });
  return groups;
}

export default function ExplainersPlot({ explainer, scope }) {
  const { enqueueSnackbar } = useSnackbar();
  const [groups, setGroups] = useState([]);
  const [currentGroup, setCurrentGroup] = useState(0);
  const [loading, setLoading] = useState(true);
  const { t } = useTranslation(["explainers"]);

  const getExplainerPlot = async () => {
    setLoading(true);
    try {
      const response = await getExplainerPlotRequest(explainer.id, scope);
      if (!response || response.length === 0) {
        setGroups([]);
        setCurrentGroup(0);
        enqueueSnackbar(t("explainers:error.noData"), {
          variant: "warning",
        });
      } else {
        setGroups(groupArtifacts(parseExplanationArtifacts(response)));
        // Reset currentGroup when data updates to avoid stale index
        setCurrentGroup(0);
      }
    } catch (error) {
      setGroups([]);
      setCurrentGroup(0);
      enqueueSnackbar(t("explainers:error.fetchExplainers"), {
        variant: "error",
      });
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (explainer.status === 3) {
      getExplainerPlot();
    }
  }, [explainer.id, explainer.status]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        maxWidth: 700,
        border: 1,
        borderColor: "divider",
        bgcolor: "background.default",
        borderRadius: 1,
        overflow: "hidden",
        p: 1,
      }}
    >
      {!loading && groups.length > 1 && (
        <FormControl variant="outlined" sx={{ minWidth: "200px", mb: 2 }}>
          <InputLabel id="select-type-label">
            {t("explainers:label.selectInstance")}
          </InputLabel>
          <Select
            id="select-type"
            value={currentGroup}
            onChange={(event) => setCurrentGroup(event.target.value)}
            label="class"
            autoWidth
          >
            {groups.map((group, i) => (
              <MenuItem key={i} value={i}>
                {group.title ??
                  t("explainers:label.instanceNumber", { number: i + 1 })}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      {!loading && explainer.status === 3 ? (
        groups.length > 0 && groups[currentGroup] ? (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
            {groups[currentGroup].title && (
              <Typography variant="subtitle2">
                {groups[currentGroup].title}
              </Typography>
            )}
            {groups[currentGroup].artifacts.map((artifact, i) => (
              <ArtifactRenderer
                key={i}
                artifact={{ ...artifact, title: null }}
              />
            ))}
          </Box>
        ) : (
          <Box sx={{ p: 2 }}>{t("explainers:error.noData")}</Box>
        )
      ) : explainer.status === 4 ? (
        <Box sx={{ p: 4 }}>{t("explainers:error.explainerFailed")}</Box>
      ) : (
        <Box sx={{ display: "flex", justifyContent: "flex-start", p: 2 }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
}

ExplainersPlot.propTypes = {
  explainer: PropTypes.shape({
    explainer_name: PropTypes.string,
    id: PropTypes.number,
    parameters: PropTypes.objectOf(
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
        PropTypes.arrayOf(PropTypes.string),
      ]),
    ),
    status: PropTypes.number,
    runId: PropTypes.number,
    explanationPath: PropTypes.string,
    plot_path: PropTypes.string,
    name: PropTypes.string,
    created: PropTypes.string,
  }).isRequired,
  scope: PropTypes.string.isRequired,
};
