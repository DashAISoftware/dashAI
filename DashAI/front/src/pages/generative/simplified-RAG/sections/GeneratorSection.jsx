import { useState, useEffect, useMemo } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
  CircularProgress,
  Alert,
  AlertTitle,
  useTheme,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getGeneratorComponents } from "../../../../api/rag";
import { buildDefaultValuesFromSchemaProperties } from "../../RAG/NewSessionModal/ragFormDefaults";
import GeneratorAdvancedModal from "../advanced/GeneratorAdvancedModal";

const getDescription = (desc, i18n) => {
  if (!desc) return "";
  if (typeof desc === "string") return desc;
  if (typeof desc === "object" && (desc.en || desc.es)) {
    return desc[i18n.language] || desc.en || desc.es || "";
  }
  return "";
};

export default function GeneratorSection({
  generatorModel,
  setGeneratorModel,
  chunkSize = 0,
  topK = 0,
  promptTokenCount = 0,
  setIsValid,
}) {
  const theme = useTheme();
  const { t, i18n } = useTranslation(["generative"]);
  const [generators, setGenerators] = useState([]);
  const [selectedGenerator, setSelectedGenerator] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);
  const DEFAULT_CONTEXT_WINDOW = 10000;
  const DEFAULT_MAX_TOKENS = 1000;
  const [initialModelParams, setInitialModelParams] = useState(null);


  const isAdvanced = useMemo(() => {
    if (!selectedGenerator || !generatorModel?.params || !initialModelParams) return false;
    return Object.keys(generatorModel.params).some(key => {
      return generatorModel.params[key] !== initialModelParams[key];
    });
  }, [selectedGenerator, generatorModel?.params, initialModelParams]);

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
        
        if (generatorModel?.component) {
          const found = data?.find((g) => g.name === generatorModel.component);
          if (found) setSelectedGenerator(found);
        }
      } catch (error) {
        console.error("Error loading generators:", error);
      } finally {
        setLoading(false);
      }
    };
    loadGenerators();
  }, []);

  const handleGeneratorChange = (event, newValue) => {
    setSelectedGenerator(newValue);
    if (newValue) {
      const initialParams = buildDefaultValuesFromSchemaProperties(newValue.schema?.properties || {});
      const overriddenParams = {
        ...initialParams,
        max_tokens: DEFAULT_MAX_TOKENS,
        context_window: DEFAULT_CONTEXT_WINDOW,
      };
      setInitialModelParams({...overriddenParams});

      setGeneratorModel({
        component: newValue.name,
        params: {...overriddenParams},
      });
    } else {
      setInitialModelParams(null);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" sx={{ minHeight: 120 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <Box display="flex" flexDirection="column" gap={2} width="100%">
        <Typography variant="body2" color="textSecondary">
          {t("generative:simplifiedRag.generator.description")}
        </Typography>

        {/* Model Selection */}
        <Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {t("generative:simplifiedRag.generator.modelLabel")}
            </Typography>
            {isAdvanced && (
              <Typography variant="caption" sx={{ color: "warning.main", fontWeight: "bold" }}>
                {t("generative:simplifiedRag.generator.advancedApplied")}
              </Typography>
            )}
          </Box>
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
                sx={{
                  "& .MuiOutlinedInput-root": isAdvanced ? {
                    "& fieldset": { borderColor: theme.palette.warning.main },
                    "&:hover fieldset": { borderColor: theme.palette.warning.main },
                    "&.Mui-focused fieldset": { borderColor: theme.palette.warning.main },
                  } : {}
                }}
              />
            )}
          />
        </Box>

        {/* Selected Model Info & Context Message */}
        {selectedGenerator && generatorModel?.params && (
          <Box
            sx={{
              p: 2,
              backgroundColor: "action.hover",
              border: "1px solid",
              borderColor: contextStats.isValid ? (isAdvanced ? "warning.main" : "divider") : "error.main",
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

        <Button
          variant="outlined"
          color="primary"
          onClick={() => setShowAdvanced(true)}
          fullWidth
          disabled={!selectedGenerator}
        >
          ↗ {t("generative:simplifiedRag.generator.advancedButton")}
        </Button>
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


GeneratorSection.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  chunkSize: PropTypes.number,
  topK: PropTypes.number,
  setIsValid: PropTypes.func.isRequired,
};
