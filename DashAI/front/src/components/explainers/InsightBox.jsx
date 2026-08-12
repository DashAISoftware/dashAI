import { React, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, FormControl, MenuItem, Select } from "@mui/material";
import { LoadingButton } from "@mui/lab";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";

import { getComponents } from "../../api/component";
import {
  createExplainerInsight,
  getInsight,
  getLatestExplainerInsight,
} from "../../api/insight";
import { startJobPolling } from "../../utils/jobPoller";
import ArtifactViewer from "../shared/ArtifactViewer";

const IN_PROGRESS_STATUSES = ["DELIVERED", "STARTED"];

/**
 * Button + model picker that requests an AI-generated insight for one
 * explainer artifact (identified by its exact `title`, the same value
 * `StoryBox` already shows as its label) and renders the result once the
 * backing job finishes. Sits alongside `StoryBox`: the deterministic
 * narrative and the AI-generated one are independent and both stay visible.
 *
 * On mount, checks whether an insight was already generated for this exact
 * artifact (e.g. in a previous visit, or before switching to a different
 * curve/instance and back) and shows it right away instead of only ever
 * showing what was just generated in this component's own lifetime. A
 * request still in progress when the component unmounted is resumed too.
 */
export default function InsightBox({ explainerId, scope, artifactTitle }) {
  const { t, i18n } = useTranslation(["explainers"]);
  const { enqueueSnackbar } = useSnackbar();
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [generating, setGenerating] = useState(false);
  const [resultText, setResultText] = useState(null);

  const watchInsightJob = (jobId, insightResultId) => {
    startJobPolling(
      jobId,
      async () => {
        try {
          const insight = await getInsight(insightResultId);
          if (insight.status === "FINISHED") {
            setResultText(insight.result_text);
          } else {
            enqueueSnackbar(
              t("explainers:error.insightJobFailed", {
                error: insight.error_message || "Unknown error",
              }),
              { variant: "error" },
            );
          }
        } finally {
          setGenerating(false);
        }
      },
      (result) => {
        setGenerating(false);
        enqueueSnackbar(
          t("explainers:error.insightJobFailed", {
            error: result.error || "Unknown error",
          }),
          { variant: "error" },
        );
      },
    );
  };

  useEffect(() => {
    let active = true;
    getComponents({ selectTypes: ["GenerativeModel"] })
      .then((components) => {
        if (!active) return;
        setModels(components);
        if (components.length > 0) setSelectedModel(components[0].name);
      })
      .catch(() => {
        if (active) setModels([]);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!artifactTitle) return;
    let active = true;
    setResultText(null);
    getLatestExplainerInsight(scope, explainerId, artifactTitle)
      .then((latest) => {
        if (!active) return;
        if (latest.status === "FINISHED") {
          setResultText(latest.result_text);
        } else if (IN_PROGRESS_STATUSES.includes(latest.status)) {
          setGenerating(true);
          watchInsightJob(latest.huey_id, latest.insight_result_id);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [scope, explainerId, artifactTitle]);

  if (!artifactTitle) return null;

  const handleGenerate = async () => {
    if (!selectedModel) return;
    setGenerating(true);
    setResultText(null);
    try {
      const response = await createExplainerInsight(
        scope,
        explainerId,
        artifactTitle,
        selectedModel,
        i18n.language?.split("-")[0] ?? "en",
      );
      watchInsightJob(response.id, response.insight_result_id);
    } catch (error) {
      setGenerating(false);
      enqueueSnackbar(t("explainers:error.insightJobEnqueueError"), {
        variant: "error",
      });
      console.error(error);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <Select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            displayEmpty
            disabled={models.length === 0 || generating}
          >
            {models.length === 0 && (
              <MenuItem value="" disabled>
                {t("explainers:error.noGenerativeModels")}
              </MenuItem>
            )}
            {models.map((model) => (
              <MenuItem key={model.name} value={model.name}>
                {model.display_name || model.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <LoadingButton
          variant="outlined"
          size="small"
          startIcon={<AutoAwesomeIcon />}
          loading={generating}
          disabled={!selectedModel}
          onClick={handleGenerate}
        >
          {t("explainers:button.generateInsight")}
        </LoadingButton>
      </Box>
      {resultText && (
        <ArtifactViewer
          artifact={{
            type: "text",
            title: `${t("explainers:label.insightTitle")} — ${artifactTitle}`,
            payload: resultText,
          }}
        />
      )}
    </Box>
  );
}

InsightBox.propTypes = {
  explainerId: PropTypes.number.isRequired,
  scope: PropTypes.string.isRequired,
  artifactTitle: PropTypes.string,
};
