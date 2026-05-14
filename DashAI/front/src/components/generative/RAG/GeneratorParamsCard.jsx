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
import GeneratorBody from "../../../pages/generative/simplified-RAG/components/GeneratorBody";

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
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                {t("generative:simplifiedRag.generator.modelLabel")}
              </Typography>
              {isExpanded && isAdvanced && (
                <Typography variant="caption" sx={{ color: "warning.main", fontWeight: "bold" }}>
                  {t("generative:simplifiedRag.generator.advancedApplied")}
                </Typography>
              )}
            </Box>
            <Box>
              {isExpanded && (
                <Tooltip title={t("generative:simplifiedRag.generator.description")}>
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
              <Tooltip title={isExpanded ? (t("generative:simplifiedRag.prompt.collapse") || "Collapse") : (t("generative:simplifiedRag.prompt.expand") || "Expand")}>
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
              {t("generative:simplifiedRag.generator.description")}
            </Typography>
          )}
        </Box>

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
