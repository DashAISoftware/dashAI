import { useState, useEffect, useMemo } from "react";
import {
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Button,
  CircularProgress,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getChunkingComponents } from "../../../../api/rag";
import { buildDefaultValuesFromSchemaProperties } from "../../RAG/NewSessionModal/ragFormDefaults";
import { getModelFromSubform, getParamsFromSubform } from "../../../../utils/schema";
import ChunkingAdvancedModal from "../advanced/ChunkingAdvancedModal";
import { useTheme } from "@mui/material/styles";

export default function ChunkingSection({
  chunkingModel,
  setChunkingModel,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["generative"]);

  const CHUNKING_PRESETS = useMemo(() => [
    {
      value: "small",
      label: t("generative:simplifiedRag.chunking.presets.small.label"),
      description: t("generative:simplifiedRag.chunking.presets.small.description"),
      config: { chunk_size: 256, chunk_overlap: 25 },
    },
    {
      value: "paragraph",
      label: t("generative:simplifiedRag.chunking.presets.paragraph.label"),
      description: t("generative:simplifiedRag.chunking.presets.paragraph.description"),
      config: { chunk_size: 500, chunk_overlap: 50 },
    },
    {
      value: "page",
      label: t("generative:simplifiedRag.chunking.presets.page.label"),
      description: t("generative:simplifiedRag.chunking.presets.page.description"),
      config: { chunk_size: 2000, chunk_overlap: 200 },
    },
    {
      value: "large",
      label: t("generative:simplifiedRag.chunking.presets.large.label"),
      description: t("generative:simplifiedRag.chunking.presets.large.description"),
      config: { chunk_size: 4000, chunk_overlap: 400 },
    },
  ], [t]);

  const CUSTOM_PRESET = useMemo(() => ({
    value: "custom",
    label: t("generative:simplifiedRag.chunking.presets.custom.label"),
    description: t("generative:simplifiedRag.chunking.presets.custom.description"),
  }), [t]);

  const [chunkers, setChunkers] = useState([]);
  const [selectedChunker, setSelectedChunker] = useState(null);
  const [selectedPreset, setSelectedPreset] = useState("paragraph");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadChunkers = async () => {
      try {
        const data = await getChunkingComponents();
        setChunkers(data || []);
        
        if (data && data.length > 0) {
          const modelName = getModelFromSubform(chunkingModel);
          const params = getParamsFromSubform(chunkingModel) ?? chunkingModel?.params;

          if (modelName) {
            const found = data.find((c) => c.name === modelName);
            if (found) {
              setSelectedChunker(found);
              updatePresetFromParams(params);
            } else {
              selectDefaultChunker(data);
            }
          } else {
            selectDefaultChunker(data);
          }
        }
      } catch (error) {
        console.error("Error loading chunkers:", error);
      } finally {
        setLoading(false);
      }
    };
    loadChunkers();
  }, []);

  // Update preset when chunkingModel.params changes (e.g. from Advanced Modal)
  useEffect(() => {
    const params = getParamsFromSubform(chunkingModel) ?? chunkingModel?.params;
    if (params) {
      updatePresetFromParams(params);
    }
  }, [chunkingModel, CHUNKING_PRESETS]);

  const updatePresetFromParams = (params) => {
    const preset = CHUNKING_PRESETS.find(p => 
      p.config.chunk_size === params?.chunk_size &&
      p.config.chunk_overlap === params?.chunk_overlap
    );
    if (preset) {
      setSelectedPreset(preset.value);
    } else {
      setSelectedPreset("custom");
    }
  };

  const selectDefaultChunker = (availableChunkers) => {
    const defaultChunker = availableChunkers.find(c => c.name === "SimpleChunker") || availableChunkers[0];
    const preset = CHUNKING_PRESETS.find(p => p.value === "paragraph");
    applyPreset(defaultChunker, preset);
  };

  const applyPreset = (chunker, preset) => {
    setSelectedChunker(chunker);
    setSelectedPreset(preset?.value || "custom");
    
    const defaultParams = buildDefaultValuesFromSchemaProperties(chunker.schema?.properties || {});
    const params = {
      ...defaultParams,
      ...(preset?.config || {}),
    };

    setChunkingModel({
      component: chunker.name,
      params,
    });
  };

  const handlePresetChange = (event, newPresetValue) => {
    if (newPresetValue !== null && selectedChunker) {
      if (newPresetValue === "custom") {
        setSelectedPreset("custom");
        return;
      }
      const preset = CHUNKING_PRESETS.find(p => p.value === newPresetValue);
      applyPreset(selectedChunker, preset);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" sx={{ minHeight: 120 }}>
        <CircularProgress />
      </Box>
    );
  }

  const allPresets = [...CHUNKING_PRESETS];
  if (selectedPreset === "custom") {
    allPresets.push(CUSTOM_PRESET);
  }

  return (
    <>
      <Box display="flex" flexDirection="column" gap={2} width="100%">
        <Typography variant="body2" color="textSecondary">
          {t("generative:simplifiedRag.chunking.description")}
        </Typography>

        {/* Preset Options */}
        <ToggleButtonGroup
          value={selectedPreset}
          exclusive
          onChange={handlePresetChange}
          fullWidth
          sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}
        >
          {allPresets.map((preset) => {
            return (
              <ToggleButton
                key={preset.value}
                value={preset.value}
                sx={{
                  flex: 1,
                  minWidth: 150,
                  textAlign: "center",
                  py: 2,
                  px: 1,
                  border: "1px solid",
                  borderColor: "divider",
                  "&.Mui-selected": {
                    color: theme.palette.primary.main,
                    border: `1px solid ${theme.palette.accent.amberBorder}`,
                    background: theme.palette.accent.amberDim,
                    borderRadius: "2px",
                    "&:hover": {
                      backgroundColor: theme.palette.primary.main,
                      color: theme.palette.primary.contrastText,
                    },
                  },
                }}
              >
                <Box display="flex" flexDirection="column" gap={0.5}>
                  <Typography variant="subtitle2">{preset.label}</Typography>
                  <Typography variant="caption">{preset.description}</Typography>
                </Box>
              </ToggleButton>
            );
          })}
        </ToggleButtonGroup>

        {/* Advanced Configuration Button */}
        <Button
          variant="outlined"
          color="primary"
          onClick={() => setShowAdvanced(true)}
          fullWidth
          disabled={!selectedChunker}
        >
          ↗ {t("generative:simplifiedRag.chunking.advancedButton")}
        </Button>
      </Box>

      {/* Advanced Configuration Modal */}
      {selectedChunker && (
        <ChunkingAdvancedModal
          open={showAdvanced}
          onClose={() => setShowAdvanced(false)}
          chunkingModel={chunkingModel}
          setChunkingModel={setChunkingModel}
        />
      )}
    </>
  );
}


ChunkingSection.propTypes = {
  chunkingModel: PropTypes.object,
  setChunkingModel: PropTypes.func.isRequired,
};
