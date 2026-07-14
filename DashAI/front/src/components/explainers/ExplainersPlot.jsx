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
import ArtifactViewer from "../shared/ArtifactViewer";

/** Wrap legacy plotly JSON strings as plotly artifacts; pass typed dicts through. */
function parseExplanationArtifacts(items) {
  return items.map((item) =>
    typeof item === "string"
      ? { type: "plotly", payload: item, title: null, role: "explanation" }
      : item,
  );
}

/**
 * Group consecutive artifacts sharing the same non-null title into one
 * instance group, tracking each artifact's flat index in the endpoint
 * response so edits can target it.
 */
function groupArtifacts(artifacts) {
  const groups = [];
  artifacts.forEach((artifact, index) => {
    const withIndex = { ...artifact, index };
    const lastGroup = groups[groups.length - 1];
    if (
      artifact.title != null &&
      lastGroup &&
      lastGroup.title === artifact.title
    ) {
      lastGroup.artifacts.push(withIndex);
    } else {
      groups.push({ title: artifact.title ?? null, artifacts: [withIndex] });
    }
  });
  return groups;
}

export default function ExplainersPlot({
  explainer,
  scope,
  onSaveOverride = null,
  onResetOverride = null,
  overriddenIndexes = [],
}) {
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
        enqueueSnackbar(t("explainers:error.noData"), { variant: "warning" });
      } else {
        setGroups(groupArtifacts(parseExplanationArtifacts(response)));
        setCurrentGroup(0);
      }
    } catch (error) {
      setGroups([]);
      setCurrentGroup(0);
      enqueueSnackbar(t("explainers:error.fetchExplainers"), {
        variant: "error",
      });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (explainer.status === 3) getExplainerPlot();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [explainer.id, explainer.status]);

  if (loading || explainer.status !== 3) {
    if (explainer.status === 4) {
      return <Box sx={{ p: 4 }}>{t("explainers:error.explainerFailed")}</Box>;
    }
    return (
      <Box sx={{ display: "flex", justifyContent: "flex-start", p: 2 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (groups.length === 0 || !groups[currentGroup]) {
    return <Box sx={{ p: 2 }}>{t("explainers:error.noData")}</Box>;
  }

  const group = groups[currentGroup];
  const inputArtifacts = group.artifacts.filter((a) => a.role === "input");
  const explanationArtifacts = group.artifacts.filter(
    (a) => a.role !== "input",
  );
  const hasSelector = groups.length > 1;

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", width: "100%", gap: 3 }}
    >
      {hasSelector ? (
        <FormControl variant="outlined" size="small" sx={{ minWidth: 220 }}>
          <InputLabel id="select-instance-label">
            {t("explainers:label.selectInstance")}
          </InputLabel>
          <Select
            labelId="select-instance-label"
            value={currentGroup}
            onChange={(event) => setCurrentGroup(event.target.value)}
            label={t("explainers:label.selectInstance")}
          >
            {groups.map((g, i) => (
              <MenuItem key={i} value={i}>
                {g.title ??
                  t("explainers:label.instanceNumber", { number: i + 1 })}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ) : (
        group.title && (
          <Typography variant="subtitle2" color="text.secondary">
            {group.title}
          </Typography>
        )
      )}

      {inputArtifacts.length > 0 && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ lineHeight: 1.4 }}
          >
            {t("explainers:label.modelInput")}
          </Typography>
          {inputArtifacts.map((artifact) => (
            <ArtifactViewer key={artifact.index} artifact={artifact} />
          ))}
        </Box>
      )}

      {explanationArtifacts.map((artifact) => (
        <ArtifactViewer
          key={artifact.index}
          artifact={artifact}
          canReset={overriddenIndexes.includes(artifact.index)}
          onSaveEdit={
            onSaveOverride
              ? (figure) => onSaveOverride(artifact.index, figure)
              : null
          }
          onResetEdit={
            onResetOverride ? () => onResetOverride(artifact.index) : null
          }
        />
      ))}
    </Box>
  );
}

ExplainersPlot.propTypes = {
  explainer: PropTypes.shape({
    id: PropTypes.number,
    status: PropTypes.number,
  }).isRequired,
  scope: PropTypes.string.isRequired,
  onSaveOverride: PropTypes.func,
  onResetOverride: PropTypes.func,
  overriddenIndexes: PropTypes.arrayOf(PropTypes.number),
};
