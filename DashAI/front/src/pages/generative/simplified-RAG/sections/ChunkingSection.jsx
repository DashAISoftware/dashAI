import { useState, useMemo } from "react";
import {
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Button,
  Dialog,
} from "@mui/material";
import PropTypes from "prop-types";
import ChunkingAdvancedModal from "../advanced/ChunkingAdvancedModal";

const CHUNKING_PRESETS = [
  {
    value: "small",
    label: "Small Chunks",
    description: "Fine-grained chunking (~256 tokens)",
  },
  {
    value: "paragraph",
    label: "Paragraph Length",
    description: "Standard paragraph-level chunking (~500 tokens)",
  },
  {
    value: "page",
    label: "Page Chunk",
    description: "Full page-level chunking (~2000 tokens)",
  },
  {
    value: "large",
    label: "Large Sections",
    description: "Large section chunking (~4000 tokens)",
  },
];

export default function ChunkingSection({
  chunkingModel,
  setChunkingModel,
}) {
  const [selectedPreset, setSelectedPreset] = useState("paragraph");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handlePresetChange = (event, newPreset) => {
    if (newPreset !== null) {
      setSelectedPreset(newPreset);
      
      // Update chunking model based on preset
      const presetConfigs = {
        small: { chunk_size: 256, chunk_overlap: 25 },
        paragraph: { chunk_size: 500, chunk_overlap: 50 },
        page: { chunk_size: 2000, chunk_overlap: 200 },
        large: { chunk_size: 4000, chunk_overlap: 400 },
      };

      const config = presetConfigs[newPreset];
      if (config) {
        setChunkingModel({
          component: "SimpleChunker",
          params: config,
        });
      }
    }
  };

  const selectedPresetInfo = CHUNKING_PRESETS.find(
    (p) => p.value === selectedPreset
  );

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
          {CHUNKING_PRESETS.map((preset) => (
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
          ))}
        </ToggleButtonGroup>

        {/* Advanced Configuration Button */}
        <Button
          variant="outlined"
          color="primary"
          onClick={() => setShowAdvanced(true)}
          fullWidth
        >
          ↗ Open Advanced Configuration
        </Button>
      </Box>

      {/* Advanced Configuration Modal */}
      <ChunkingAdvancedModal
        open={showAdvanced}
        onClose={() => setShowAdvanced(false)}
        chunkingModel={chunkingModel}
        setChunkingModel={setChunkingModel}
      />
    </>
  );
}

ChunkingSection.propTypes = {
  chunkingModel: PropTypes.object,
  setChunkingModel: PropTypes.func.isRequired,
};
