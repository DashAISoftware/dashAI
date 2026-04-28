import { useState, useEffect, useMemo } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
  CircularProgress,
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
}) {
  const { i18n } = useTranslation();
  const [generators, setGenerators] = useState([]);
  const [selectedGenerator, setSelectedGenerator] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);

  // Check if current configuration is "advanced"
  const isAdvanced = useMemo(() => {
    if (!selectedGenerator || !generatorModel?.params) return false;
    
    // Get default params for this component
    const defaultParams = buildDefaultValuesFromSchemaProperties(selectedGenerator.schema?.properties || {});
    
    // Check if any param is different from default
    // We stringify to handle objects/arrays comparison
    return Object.keys(generatorModel.params).some(key => {
      return JSON.stringify(generatorModel.params[key]) !== JSON.stringify(defaultParams[key]);
    });
  }, [selectedGenerator, generatorModel?.params]);

  useEffect(() => {
    const loadGenerators = async () => {
      try {
        const data = await getGeneratorComponents();
        setGenerators(data || []);
        
        // Try to restore previously selected generator
        if (generatorModel?.component) {
          const found = data?.find((g) => g.name === generatorModel.component);
          if (found) {
            setSelectedGenerator(found);
          }
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
      setGeneratorModel({
        component: newValue.name,
        params: initialParams,
      });
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
          Select the language model that will generate responses based on the
          retrieved context and your prompts.
        </Typography>

        {/* Model Selection */}
        <Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              Generator Model
            </Typography>
            {isAdvanced && (
              <Typography variant="caption" sx={{ color: "warning.main", fontWeight: "bold" }}>
                ADVANCED CONFIGURATION APPLIED
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
                label="Select language model"
                placeholder="e.g., GPT-4, Claude, Llama"
                sx={{
                  "& .MuiOutlinedInput-root": isAdvanced ? {
                    "& fieldset": { borderColor: "warning.main" },
                    "&:hover fieldset": { borderColor: "warning.dark" },
                    "&.Mui-focused fieldset": { borderColor: "warning.main" },
                  } : {}
                }}
              />
            )}
            sx={{
              "& .MuiAutocomplete-option": {
                fontSize: "0.875rem",
              },
            }}
          />
        </Box>

        {/* Selected Model Info */}
        {selectedGenerator && (
          <Box
            sx={{
              p: 2,
              backgroundColor: "action.hover",
              border: "1px solid",
              borderColor: isAdvanced ? "warning.main" : "divider",
              borderRadius: 1,
            }}
          >
            <Typography variant="body2">
              <strong>Model:</strong> {selectedGenerator.name}
              {getDescription(selectedGenerator.description, i18n) && (
                <>
                  <br />
                  <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                    {getDescription(selectedGenerator.description, i18n)}
                  </Typography>
                </>
              )}
            </Typography>
          </Box>
        )}

        {/* Advanced Configuration Button */}
        <Button
          variant="outlined"
          color="primary"
          onClick={() => setShowAdvanced(true)}
          fullWidth
          disabled={!selectedGenerator}
        >
          ↗ Open Advanced Configuration
        </Button>
      </Box>

      {/* Advanced Configuration Modal */}
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
};
