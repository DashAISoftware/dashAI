import { useState, useEffect, useMemo } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
  Alert,
  AlertTitle,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getGeneratorComponents } from "../../../../api/rag";
import { resolveDefaults } from "../../../../utils/schema";
import GeneratorAdvancedModal from "../advanced/GeneratorAdvancedModal";
import AdvancedConfigCard from "../components/AdvancedConfigCard";
import RAGSectionColumn from "../components/RAGSectionColumn";
import { getDescription } from "../components/sectionUtils";

export default function GeneratorSection({
  generatorModel,
  setGeneratorModel,
  chunkSize = 0,
  topK = 0,
  promptTokenCount = 0,
  setIsValid,
}) {
  const { t, i18n } = useTranslation(["generative"]);
  const [generators, setGenerators] = useState([]);
  const [selectedGenerator, setSelectedGenerator] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);
  const DEFAULT_CONTEXT_WINDOW = 10000;
  const DEFAULT_MAX_TOKENS = 1000;

  const contextStats = useMemo(() => {
    if (!generatorModel?.params || !selectedGenerator || !generatorModel.component) {
      return { isValid: false, availableTokens: 0 };
    }

    const contextWindow = generatorModel.params.context_window ?? DEFAULT_CONTEXT_WINDOW;
    const maxTokens = generatorModel.params.max_tokens ?? DEFAULT_MAX_TOKENS;
    const chunkTokens = chunkSize * topK;
    const availableForMessage = contextWindow - chunkTokens - promptTokenCount - maxTokens;
    const isValid = availableForMessage > 0;

    return {
      isValid,
      availableTokens: Math.max(0, Math.floor(availableForMessage))
    };
  }, [generatorModel?.params, generatorModel?.component, selectedGenerator, chunkSize, topK, promptTokenCount]);

  const isRemoteModel = useMemo(() => {
    if (!selectedGenerator || !generatorModel?.component) return false;
    const name = (selectedGenerator.name || "").toLowerCase();
    return name.includes("openai") || name.includes("deepseek");
  }, [selectedGenerator, generatorModel?.component]);

  const isApiKeyMissing = useMemo(() => {
    if (!isRemoteModel || !generatorModel?.params) return false;
    return !generatorModel.params.API_key;
  }, [isRemoteModel, generatorModel?.params]);

  const overallIsValid = contextStats.isValid && !isApiKeyMissing;

  useEffect(() => {
    setIsValid(overallIsValid);
  }, [overallIsValid, setIsValid]);

  useEffect(() => {
    const loadGenerators = async () => {
      try {
        const data = await getGeneratorComponents();
        setGenerators(data || []);
      } catch (error) {
        console.error("Error loading generators:", error);
      } finally {
        setLoading(false);
      }
    };
    loadGenerators();
  }, []);

  useEffect(() => {
    if (!generators.length) return;

    if (!generatorModel?.component) {
      return;
    }

    const foundGenerator = generators.find((generator) => {
      return generator.name === generatorModel.component;
    });

    if (!foundGenerator) return;

    const selectedGeneratorName = selectedGenerator?.name || null;
    const currentGeneratorName = generatorModel.component;

    if (selectedGeneratorName === currentGeneratorName) {
      return;
    }

    setSelectedGenerator(foundGenerator);
  }, [generators, generatorModel?.component, generatorModel?.params]);

  const handleGeneratorChange = async (event, newValue) => {
    if (!newValue) {
      setSelectedGenerator(null);
      setGeneratorModel({ component: "", params: {} });
      return;
    }

    const initialParams = await resolveDefaults(newValue.name);
    const overriddenParams = {
      ...initialParams,
      max_tokens: DEFAULT_MAX_TOKENS,
      context_window: DEFAULT_CONTEXT_WINDOW,
    };

    setSelectedGenerator(newValue);
    setGeneratorModel({
      component: newValue.name,
      params: { ...overriddenParams },
    });
  };

  if (loading) {
    return null;
  }

  return (
    <RAGSectionColumn>
      <Typography variant="body2" color="textSecondary">
        {t("generative:simplifiedRag.generator.description")}
      </Typography>

      <Box>
        <Autocomplete
          options={generators}
          value={selectedGenerator}
          onChange={handleGeneratorChange}
          getOptionLabel={(option) => getDescription(option.display_name, i18n) || option.name || ""}
          isOptionEqualToValue={(option, value) => option?.name === value?.name}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("generative:simplifiedRag.generator.selectModel")}
              placeholder={t("generative:simplifiedRag.generator.selectModelPlaceholder")}
            />
          )}
        />
      </Box>

      {selectedGenerator && (
        <Box
          sx={{
            p: 2,
            backgroundColor: "action.hover",
            border: "1px solid",
            borderColor: contextStats.isValid ? "divider" : "error.main",
            borderRadius: 1,
            display: "flex",
            flexDirection: "column",
            gap: 1
          }}
        >
          <Typography variant="body2">
            <Box component="span" sx={{ typography: "subtitle2" }}>
              {t("generative:simplifiedRag.generator.modelInfo")}
            </Box> {selectedGenerator.name}
          </Typography>

          <Typography variant="body2" sx={{ color: contextStats.isValid ? "success.main" : "error.main", fontWeight: 500 }}>
            {t("generative:validation.contextSpace", { availableChars: contextStats.availableTokens?.toLocaleString() })}
          </Typography>

          {!contextStats.isValid && (
            <Alert severity="error" sx={{ mt: 1 }}>
              <AlertTitle>{t("generative:validation.insufficientContextTitle")}</AlertTitle>
              {t("generative:validation.insufficientContextDescription")}
            </Alert>
          )}

          {isApiKeyMissing && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              <AlertTitle>{t("generative:validation.apiKeyMissingTitle")}</AlertTitle>
              {t("generative:validation.apiKeyMissingDescription")}
            </Alert>
          )}

          {getDescription(selectedGenerator.description, i18n) && (
            <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
              {getDescription(selectedGenerator.description, i18n)}
            </Typography>
          )}
        </Box>
      )}

      <Button
        variant="outlined"
        color="primary"
        onClick={() => setShowAdvanced(true)}
        fullWidth
        disabled={!selectedGenerator}
      >
        ↗ {t("generative:simplifiedRag.generator.advancedButton")}
      </Button>

      {selectedGenerator && (
        <GeneratorAdvancedModal
          open={showAdvanced}
          onClose={() => setShowAdvanced(false)}
          selectedGenerator={selectedGenerator}
          generatorModel={generatorModel}
          setGeneratorModel={setGeneratorModel}
        />
      )}
    </RAGSectionColumn>
  );
}

GeneratorSection.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  chunkSize: PropTypes.number,
  topK: PropTypes.number,
  promptTokenCount: PropTypes.number,
  setIsValid: PropTypes.func.isRequired,
};
