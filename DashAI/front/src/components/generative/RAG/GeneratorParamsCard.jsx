import { useState, useMemo } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import InfoIcon from "@mui/icons-material/Info";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import GeneratorBody from "../../../pages/generative/RAGSession/components/GeneratorBody";
import RAGSectionColumn from "../../../pages/generative/RAGSession/components/RAGSectionColumn";

/**
 * Card for configuring the generation model parameters, with expand/collapse
 * and an "advanced" indicator when non-default parameter values are set.
 *
 * @param {object}   props
 * @param {object}   props.generatorModel - { component: string|null, params: object }
 * @param {function} props.setGeneratorModel - State setter for generatorModel.
 * @param {number}   [props.chunkSize=0] - Chunk size used by the retriever.
 * @param {number}   [props.topK=0] - Top-K value used by the retriever.
 * @param {number}   [props.promptTokenCount=0] - Token count of the selected prompt.
 * @param {function} props.setIsValid - Callback to set the validity state of the form.
 * @returns {JSX.Element}
 */
export default function GeneratorParamsCard({
  generatorModel,
  setGeneratorModel,
  chunkSize = 0,
  topK = 0,
  promptTokenCount = 0,
  setIsValid,
}) {
  const { t } = useTranslation(["generative"]);
  const [showDescription, setShowDescription] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [initialModelParams, setInitialModelParams] = useState(null);

  /** Whether any generator parameter differs from its initial (default) values. */
  const isAdvanced = useMemo(() => {
    if (!generatorModel?.component || !generatorModel?.params || !initialModelParams) return false;
    return Object.keys(generatorModel.params).some(key => {
      return generatorModel.params[key] !== initialModelParams[key];
    });
  }, [generatorModel?.params, initialModelParams]);

  return (
    <Card sx={{ width: "100%", backgroundColor: "background.paper" }}>
      <CardContent sx={{ p: 2 }}>
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Box>
              <Typography variant="subtitle2">
                {t("generative:rag.generator.modelLabel")}
              </Typography>
              {isExpanded && isAdvanced && (
                <Typography variant="caption" sx={{ color: "warning.main" }}>
                  {t("generative:rag.generator.advancedApplied")}
                </Typography>
              )}
            </Box>
            <Box>
              {isExpanded && (
                <Tooltip title={t("generative:rag.generator.description")}>
                  <IconButton
                    size="small"
                    onClick={() => setShowDescription((s) => !s)}
                    aria-label="generator-info"
                    sx={{ color: "text.secondary" }}
                  >
                    <InfoIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              <Tooltip title={isExpanded ? t("generative:rag.prompt.collapse") : t("generative:rag.prompt.expand")}>
                <IconButton
                  size="small"
                  onClick={() => setIsExpanded((s) => !s)}
                  aria-label="toggle-generator-card"
                >
                  <ExpandMoreIcon
                    fontSize="small"
                    sx={{ transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}
                  />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          {isExpanded && showDescription && (
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              {t("generative:rag.generator.description")}
            </Typography>
          )}
        </Box>

        <RAGSectionColumn>
          <GeneratorBody
            generatorModel={generatorModel}
            setGeneratorModel={setGeneratorModel}
            chunkSize={chunkSize}
            topK={topK}
            promptTokenCount={promptTokenCount}
            setIsValid={setIsValid}
            isAdvanced={isAdvanced}
            setInitialModelParams={setInitialModelParams}
            showDetails={isExpanded}
          />
        </RAGSectionColumn>
      </CardContent>
    </Card>
  );
}

GeneratorParamsCard.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  chunkSize: PropTypes.number,
  topK: PropTypes.number,
  promptTokenCount: PropTypes.number,
  setIsValid: PropTypes.func.isRequired,
};
