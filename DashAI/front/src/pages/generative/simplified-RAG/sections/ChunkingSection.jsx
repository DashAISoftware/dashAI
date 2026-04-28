import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Button,
  CircularProgress,
} from "@mui/material";
import PropTypes from "prop-types";
import { getChunkingComponents } from "../../../../api/rag";
import { buildDefaultValuesFromSchemaProperties } from "../../RAG/NewSessionModal/ragFormDefaults";
import ChunkingAdvancedModal from "../advanced/ChunkingAdvancedModal";

const CHUNKING_PRESETS = [
  {
    value: "small",
    label: "Small Chunks",
    description: "Fine-grained chunking (~256 tokens)",
    config: { chunk_size: 256, chunk_overlap: 25 },
  },
  {
    value: "paragraph",
    label: "Paragraph Length",
    description: "Standard paragraph-level chunking (~500 tokens)",
    config: { chunk_size: 500, chunk_overlap: 50 },
  },
  {
    value: "page",
    label: "Page Chunk",
    description: "Full page-level chunking (~2000 tokens)",
    config: { chunk_size: 2000, chunk_overlap: 200 },
  },
  {
    value: "large",
    label: "Large Sections",
    description: "Large section chunking (~4000 tokens)",
    config: { chunk_size: 4000, chunk_overlap: 400 },
  },
];

const CUSTOM_PRESET = {
  value: "custom",
  label: "Custom Chunking Model",
  description: "Advanced configuration applied",
};

export default function ChunkingSection({
  chunkingModel,
  setChunkingModel,
}) {
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
          if (chunkingModel?.component) {
            const found = data.find((c) => c.name === chunkingModel.component);
            if (found) {
              setSelectedChunker(found);
              updatePresetFromParams(chunkingModel.params);
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
    if (chunkingModel?.params) {
      updatePresetFromParams(chunkingModel.params);
    }
  }, [chunkingModel.params]);

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
          Select how your documents will be split into chunks for retrieval.
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
            const isCustom = preset.value === "custom";
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
                    backgroundColor: "primary.main",
                    color: "primary.contrastText",
                    borderColor: "primary.main",
                    "&:hover": {
                      backgroundColor: "primary.dark",
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
          ↗ Open Advanced Configuration
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
