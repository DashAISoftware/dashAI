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
import { buildDefaultValuesFromSchemaProperties } from "./ragFormDefaults";
import GeneratorAdvancedModal from "../advanced/GeneratorAdvancedModal";
import AdvancedConfigCard from "./AdvancedConfigCard";
import { getDescription } from "./sectionUtils";

export default function GeneratorBody({
  generatorModel,
  setGeneratorModel,
  chunkSize = 0,
  topK = 0,
  promptTokenCount = 0,
  setIsValid,
  isAdvanced,
  setInitialModelParams,
  showDetails = true,
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
      return { isValid: true, availableTokens: 0 };
    }

    const contextWindow = generatorModel.params.context_window || DEFAULT_CONTEXT_WINDOW;
    const maxTokens = generatorModel.params.max_tokens || DEFAULT_MAX_TOKENS;
    const chunkTokens = chunkSize * topK;
    const availableForMessage = contextWindow - chunkTokens - promptTokenCount - maxTokens;
    const isValid = availableForMessage > 0;

    return {
      isValid,
      availableTokens: Math.max(0, Math.floor(availableForMessage))
    };
  }, [generatorModel?.params, generatorModel?.component, selectedGenerator, chunkSize, topK, promptTokenCount]);

  useEffect(() => {
    setIsValid(contextStats.isValid);
  }, [contextStats.isValid, setIsValid]);

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
      setSelectedGenerator(null);
      if (setInitialModelParams) setInitialModelParams(null);
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
    if (setInitialModelParams) setInitialModelParams({ ...generatorModel.params });
  }, [generators, generatorModel?.component, generatorModel?.params]);

  const handleGeneratorChange = (event, newValue) => {
    setSelectedGenerator(newValue);
    if (newValue) {
      const initialParams = buildDefaultValuesFromSchemaProperties(newValue.schema?.properties || {});
      const overriddenParams = {
        ...initialParams,
        max_tokens: DEFAULT_MAX_TOKENS,
        context_window: DEFAULT_CONTEXT_WINDOW,
      };
      if (setInitialModelParams) setInitialModelParams({ ...overriddenParams });

      setGeneratorModel({
        component: newValue.name,
        params: { ...overriddenParams },
      });
    } else {
      if (setInitialModelParams) setInitialModelParams(null);
    }
  };

  if (loading) {
    return null;
  }

  return (
    <>
      <Box display="flex" flexDirection="column" gap={2} width="100%">
        {/* Model Selection */}
        <Box>
          <Autocomplete
            options={generators}
            value={selectedGenerator}
            onChange={handleGeneratorChange}
            getOptionLabel={(option) => option.name || ""}
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

        {isAdvanced && selectedGenerator && (
          <AdvancedConfigCard
            modelName={selectedGenerator.name}
            onClick={() => setShowAdvanced(true)}
          />
        )}

        {/* Selected Model Info & Context Message */}
        {showDetails && selectedGenerator && generatorModel?.params && (
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
              <strong>{t("generative:simplifiedRag.generator.modelInfo")}</strong> {selectedGenerator.name}
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

            {getDescription(selectedGenerator.description, i18n) && (
              <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                {getDescription(selectedGenerator.description, i18n)}
              </Typography>
            )}
          </Box>
        )}

        {showDetails && (
          <Button
            variant="outlined"
            color="primary"
            onClick={() => setShowAdvanced(true)}
            fullWidth
            disabled={!selectedGenerator}
          >
            ↗ {t("generative:simplifiedRag.generator.advancedButton")}
          </Button>
        )}
      </Box>

      {selectedGenerator && (
        <GeneratorAdvancedModal
          open={showAdvanced}
          onClose={() => setShowAdvanced(false)}
          selectedGenerator={selectedGenerator}
          generatorModel={generatorModel}
          setGeneratorModel={setGeneratorModel}
        />
      )}
    </>
  );
}

GeneratorBody.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  chunkSize: PropTypes.number,
  topK: PropTypes.number,
  promptTokenCount: PropTypes.number,
  setIsValid: PropTypes.func.isRequired,
  isAdvanced: PropTypes.bool,
  setInitialModelParams: PropTypes.func,
  showDetails: PropTypes.bool,
};
