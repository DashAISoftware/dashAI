import { React, useEffect, useState } from "react";
import { CircularProgress, Box, Typography } from "@mui/material";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";

import { getExplainerPlot as getExplainerPlotRequest } from "../../api/explainer";
import { useTranslation } from "react-i18next";
import ArtifactViewer from "../shared/ArtifactViewer";
import ExplainerInstanceTable from "./ExplainerInstanceTable";

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
  const isLocal = scope === "local";
  const datasetPath = isLocal ? explainer.input_dataset_path : null;

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
  const hasSelector = groups.length > 1;
  const instanceLabel = (g, index) =>
    g.title ?? t("explainers:label.instanceNumber", { number: index + 1 });

  // The explanation artifacts for the selected instance.
  const detail = (
    <Box
      sx={{
        flex: 1,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        gap: 3,
      }}
    >
      {group.artifacts.map((artifact) => (
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

  // Single instance: no selector needed, show the explanation full width.
  if (!hasSelector) {
    return (
      <Box
        sx={{ display: "flex", flexDirection: "column", width: "100%", gap: 3 }}
      >
        {group.title && (
          <Typography variant="subtitle2" color="text.secondary">
            {group.title}
          </Typography>
        )}
        {detail}
      </Box>
    );
  }

  // Many instances: the explained dataset rows on the left (paginated, the
  // model input for each instance), the selected instance's explanation on
  // the right.
  return (
    <Box
      sx={{ display: "flex", gap: 3, width: "100%", alignItems: "flex-start" }}
    >
      <Box sx={{ flex: "0 0 42%", minWidth: 300, maxWidth: 560 }}>
        <Typography
          variant="overline"
          color="text.secondary"
          sx={{ display: "block", mb: 1, lineHeight: 1.4 }}
        >
          {t("explainers:label.modelInput")}
        </Typography>
        <ExplainerInstanceTable
          datasetPath={datasetPath}
          titles={groups.map((g, i) => instanceLabel(g, i))}
          selectedIndex={currentGroup}
          onSelect={setCurrentGroup}
        />
      </Box>
      {detail}
    </Box>
  );
}

ExplainersPlot.propTypes = {
  explainer: PropTypes.shape({
    id: PropTypes.number,
    status: PropTypes.number,
    input_dataset_path: PropTypes.string,
  }).isRequired,
  scope: PropTypes.string.isRequired,
  onSaveOverride: PropTypes.func,
  onResetOverride: PropTypes.func,
  overriddenIndexes: PropTypes.arrayOf(PropTypes.number),
};
