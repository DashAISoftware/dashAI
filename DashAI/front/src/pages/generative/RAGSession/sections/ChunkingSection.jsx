import { useState, useEffect, useMemo } from "react";
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  useTheme,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getChunkingComponents } from "../../../../api/rag";
import {
  resolveDefaults,
  getModelFromSubform,
  getParamsFromSubform,
} from "../../../../utils/schema";
import ChunkingAdvancedModal from "../advanced/ChunkingAdvancedModal";
import AdvancedConfigCard from "../components/AdvancedConfigCard";
import PresetCard from "../components/PresetCard";
import RAGSectionColumn from "../components/RAGSectionColumn";

/**
 * Chunking strategy section.
 * Lets the user pick between preset chunk sizes (small, paragraph, page, large)
 * or open the advanced configuration modal.
 *
 * @param {object}   props
 * @param {object}   props.chunkingModel    - Current { component, params } for chunking.
 * @param {Function} props.setChunkingModel  - Sets the chunking model configuration.
 * @returns {JSX.Element} The chunking preset picker.
 */
export default function ChunkingSection({ chunkingModel, setChunkingModel }) {
  const { t } = useTranslation(["generative"]);
  const theme = useTheme();

  const CHUNKING_PRESETS = useMemo(
    () => [
      {
        value: "small",
        label: t("generative:rag.chunking.presets.small.label"),
        config: { chunk_size: 250, chunk_overlap: 25 },
      },
      {
        value: "paragraph",
        label: t("generative:rag.chunking.presets.paragraph.label"),
        config: { chunk_size: 500, chunk_overlap: 50 },
      },
      {
        value: "page",
        label: t("generative:rag.chunking.presets.page.label"),
        config: { chunk_size: 2000, chunk_overlap: 200 },
      },
      {
        value: "large",
        label: t("generative:rag.chunking.presets.large.label"),
        config: { chunk_size: 4000, chunk_overlap: 400 },
      },
    ],
    [t],
  );

  /**
   * Build a human-readable description string for a chunking preset.
   * @param {object} preset - A preset object with a `config.chunk_size` property.
   * @returns {string} Description showing chars and estimated tokens.
   */
  const getPresetDescription = (preset) => {
    const chars = preset.config.chunk_size;
    const tokens = Math.ceil(chars / 4);
    return t("generative:rag.chunking.presets.chunkSizeFormat", {
      chars,
      tokens,
    });
  };

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
          const params =
            getParamsFromSubform(chunkingModel) ?? chunkingModel?.params;

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

  /**
   * Match params against known presets and update `selectedPreset`.
   * Falls back to "custom" when no preset matches.
   * @param {object} params - Chunking parameters { chunk_size, chunk_overlap }.
   */
  const updatePresetFromParams = (params) => {
    const preset = CHUNKING_PRESETS.find(
      (p) =>
        p.config.chunk_size === params?.chunk_size &&
        p.config.chunk_overlap === params?.chunk_overlap,
    );
    if (preset) {
      setSelectedPreset(preset.value);
    } else {
      setSelectedPreset("custom");
    }
  };

  /**
   * Select the default chunker (CharacterChunkModel) and apply the "paragraph" preset.
   * @param {Array} availableChunkers - List of available chunking components.
   */
  const selectDefaultChunker = (availableChunkers) => {
    const defaultChunker =
      availableChunkers.find((c) => c.name === "CharacterChunkModel") ||
      availableChunkers[0];
    const preset = CHUNKING_PRESETS.find((p) => p.value === "paragraph");
    applyPreset(defaultChunker, preset);
  };

  /**
   * Apply a chunking preset by resolving default params and merging preset config.
   * @param {object} chunker - The chunker component to use.
   * @param {object} [preset] - The preset config to merge (or null for custom).
   */
  const applyPreset = async (chunker, preset) => {
    setSelectedChunker(chunker);
    setSelectedPreset(preset?.value || "custom");

    const defaultParams = await resolveDefaults(chunker.name);
    const params = {
      ...defaultParams,
      ...(preset?.config || {}),
    };

    setChunkingModel({
      component: chunker.name,
      params,
    });
  };

  /**
   * Handle a preset card click — toggle preset or no-op if already selected.
   * @param {string} presetValue - The preset key ("small", "paragraph", etc.).
   */
  const handlePresetClick = (presetValue) => {
    if (!selectedChunker) return;
    if (presetValue === selectedPreset) return;
    const preset = CHUNKING_PRESETS.find((p) => p.value === presetValue);
    if (preset) {
      applyPreset(selectedChunker, preset);
    }
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        sx={{ minHeight: 120 }}
      >
        <CircularProgress />
      </Box>
    );
  }

  const isCustom = selectedPreset === "custom";

  return (
    <RAGSectionColumn>
      <Typography variant="body2" color="textSecondary">
        {t("generative:rag.chunking.description")}
      </Typography>

      <Box
        sx={{
          display: "flex",
          gap: 1,
          alignItems: "stretch",
          flexWrap: "wrap",
        }}
      >
        {CHUNKING_PRESETS.map((preset) => (
          <PresetCard
            key={preset.value}
            selected={selectedPreset === preset.value}
            onClick={() => handlePresetClick(preset.value)}
            label={preset.label}
            description={getPresetDescription(preset)}
            sx={{ minWidth: 150 }}
          />
        ))}
        {isCustom && selectedChunker && (
          <AdvancedConfigCard
            modelName={selectedChunker.name}
            onClick={() => setShowAdvanced(true)}
          />
        )}
      </Box>

      <Button
        variant="contained"
        color="primary"
        size="small"
        onClick={() => setShowAdvanced(true)}
        disabled={!selectedChunker}
        sx={{
          alignSelf: "flex-start",
          width: "fit-content",
          border: "1px solid",
          borderColor: theme.palette.primary.main,
          backgroundColor: theme.palette.action.selected,
          color: theme.palette.text.primary,
        }}
      >
        ↗ {t("generative:rag.chunking.advancedButton")}
      </Button>

      {selectedChunker && (
        <ChunkingAdvancedModal
          open={showAdvanced}
          onClose={() => setShowAdvanced(false)}
          chunkingModel={chunkingModel}
          setChunkingModel={setChunkingModel}
        />
      )}
    </RAGSectionColumn>
  );
}

ChunkingSection.propTypes = {
  chunkingModel: PropTypes.object,
  setChunkingModel: PropTypes.func.isRequired,
};
