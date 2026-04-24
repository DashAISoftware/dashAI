import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  Button,
  CircularProgress,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import WarningIcon from "@mui/icons-material/WarningOutlined";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getGeneratorComponents } from "../../../../api/rag";
import GeneratorAdvancedModal from "../advanced/GeneratorAdvancedModal";

const getDescription = (desc, i18n) => {
  if (!desc) return "";
  if (typeof desc === "string") return desc;
  if (typeof desc === "object" && (desc.en || desc.es)) {
    return desc[i18n.language] || desc.en || desc.es || "";
  }
  return "";
};

// Hardcoded parameter counts for models (in billions)
const MODEL_PARAMS = {
  "GPT-4": 1000,
  "GPT-3.5": 175,
  "Claude": 100,
  "Claude-2": 100,
  "Llama-7B": 7,
  "Llama-13B": 13,
  "Llama-70B": 70,
  "Mistral": 7,
};

// Model size options and memory requirements (in GB)
const MODEL_SIZES = {
  "GPT-4": [
    { size: "small", params: "8B", memory: 16 },
    { size: "base", params: "40B", memory: 80 },
    { size: "large", params: "100B", memory: 200 },
  ],
  "GPT-3.5": [
    { size: "small", params: "7B", memory: 14 },
    { size: "base", params: "175B", memory: 350 },
  ],
  "Claude": [
    { size: "small", params: "13B", memory: 26 },
    { size: "base", params: "100B", memory: 200 },
  ],
  "Claude-2": [
    { size: "base", params: "100B", memory: 200 },
  ],
  "Llama-7B": [
    { size: "full", params: "7B", memory: 14 },
  ],
  "Llama-13B": [
    { size: "full", params: "13B", memory: 26 },
  ],
  "Llama-70B": [
    { size: "full", params: "70B", memory: 140 },
  ],
  "Mistral": [
    { size: "small", params: "7B", memory: 14 },
    { size: "large", params: "46B", memory: 92 },
  ],
};

export default function GeneratorSection({
  generatorModel,
  setGeneratorModel,
}) {
  const { i18n } = useTranslation();
  const [generators, setGenerators] = useState([]);
  const [selectedGenerator, setSelectedGenerator] = useState(null);
  const [selectedSize, setSelectedSize] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);

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
    setSelectedSize(null); // Reset size when model changes
    if (newValue) {
      setGeneratorModel({
        component: newValue.name,
        params: {},
      });
    }
  };

  const handleSizeChange = (event) => {
    const sizeName = event.target.value;
    setSelectedSize(sizeName);
    // Update generator model with size info
    if (selectedGenerator) {
      setGeneratorModel((prev) => ({
        ...prev,
        params: {
          ...prev.params,
          size: sizeName,
        },
      }));
    }
  };

  const getAvailableSizes = () => {
    if (!selectedGenerator) return [];
    return MODEL_SIZES[selectedGenerator.name] || [];
  };

  const getSelectedSizeMemory = () => {
    const sizes = getAvailableSizes();
    if (!selectedSize || sizes.length === 0) return null;
    return sizes.find((s) => s.size === selectedSize);
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
          <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
            Generator Model
          </Typography>
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
              />
            )}
            sx={{
              "& .MuiAutocomplete-option": {
                fontSize: "0.875rem",
              },
            }}
          />
        </Box>

        {/* Model Size Selection */}
        {selectedGenerator && getAvailableSizes().length > 0 && (
          <Box>
            <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
              Model Size
            </Typography>
            <FormControl fullWidth>
              <InputLabel id="model-size-label">Select model size</InputLabel>
              <Select
                labelId="model-size-label"
                id="model-size-select"
                value={selectedSize || ""}
                label="Select model size"
                onChange={handleSizeChange}
              >
                {getAvailableSizes().map((sizeOption) => (
                  <MenuItem key={sizeOption.size} value={sizeOption.size}>
                    {sizeOption.size.charAt(0).toUpperCase() + sizeOption.size.slice(1)} - {sizeOption.params} parameters
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        )}

        {/* Selected Model Info */}
        {selectedGenerator && (
          <Box
            sx={{
              p: 2,
              backgroundColor: "action.hover",
              border: "1px solid",
              borderColor: "divider",
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

            {/* Parameter count and warning */}
            {MODEL_PARAMS[selectedGenerator.name] && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: 2 }}>
                <WarningIcon sx={{ fontSize: 18, color: "warning.main" }} />
                <Typography variant="caption">
                  <strong>{MODEL_PARAMS[selectedGenerator.name]}B parameters</strong> • Recommended for your hardware
                </Typography>
              </Box>
            )}

            {/* Memory requirement based on selected size */}
            {getSelectedSizeMemory() && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" display="block" sx={{ color: "text.secondary" }}>
                  With this size, the model execution could take approximately <strong>{getSelectedSizeMemory().memory} GB</strong> of memory.
                </Typography>
              </Box>
            )}
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
