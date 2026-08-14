import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Slider,
  useTheme,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import {
  getRetrieverComponents,
  getRetrieverPresets,
} from "../../../../api/rag";
import {
  loadRetrieverKinds,
  isComposite as isCompositeKind,
} from "../retrieverKinds";
import RetrieverAdvancedModal from "../advanced/RetrieverAdvancedModal";
import AdvancedConfigCard from "../components/AdvancedConfigCard";
import PresetCard from "../components/PresetCard";
import RAGSectionColumn from "../components/RAGSectionColumn";

const TOP_K_MIN = 1;
// Default upper bound of the top-K slider. It grows only when the user has
// manually configured a larger top-K elsewhere (e.g. advanced configuration).
const TOP_K_MAX_DEFAULT = 15;

// Labels are localized in the frontend via i18n; the backend only supplies the
// resolved component/params and a language-neutral description per preset key.
const PRESET_LABEL_KEYS = {
  keyword: "generative:rag.retriever.keywordLabel",
  semantic: "generative:rag.retriever.semanticLabel",
  hybrid: "generative:rag.retriever.hybridLabel",
};

/**
 * Deep equality comparison for objects, arrays, and primitives.
 * Handles nested structures recursively. Returns false for
 * different types, null vs object, or arrays vs objects.
 */
function deepEqual(a, b) {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return false;
  if (typeof a !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  if (keysA.length !== keysB.length) return false;
  return keysA.every((k) => deepEqual(a[k], b[k]));
}

/**
 * Recursively strips `top_k` keys from a retriever params object (including
 * nested children of composite retrievers), so preset matching ignores the
 * selected top-K value at every level.
 */
function stripTopKDeep(value) {
  if (Array.isArray(value)) return value.map(stripTopKDeep);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([k]) => k !== "top_k")
        .map(([k, v]) => [k, stripTopKDeep(v)]),
    );
  }
  return value;
}

/**
 * Compute the effective top-K value for a retriever model,
 * handling composite retrievers (Parallel, Sequential, MMRReranker).
 * @param {object} model - Retriever model { component, params }.
 * @returns {number|null} The effective top-K or null.
 */
function getEffectiveTopK(model) {
  if (!model?.params) return null;
  if (model.component === "ParallelRetriever") {
    const children = model.params.children || [];
    if (children.length === 0) return null;
    return children.reduce((sum, child) => sum + (child.params?.top_k || 0), 0);
  }
  if (model.component === "SequentialRetriever") {
    const children = model.params.children || [];
    if (children.length > 0) {
      return children[children.length - 1].params?.top_k || null;
    }
    return null;
  }
  if (model.component === "MMRRerankerRetriever") {
    return typeof model.params.top_k === "number" ? model.params.top_k : null;
  }
  return typeof model.params.top_k === "number" ? model.params.top_k : null;
}

/**
 * Retriever model selection section.
 * Provides keyword / semantic / hybrid presets (fetched from the backend),
 * a top-K picker, and an advanced configuration modal for custom retrievers.
 *
 * @param {object}   props
 * @param {object}   props.retrieverModel    - Current { component, params } for the retriever.
 * @param {Function} props.setRetrieverModel  - Sets the retriever model configuration.
 * @returns {JSX.Element} The retriever preset picker.
 */
export default function RetrieverSection({
  retrieverModel,
  setRetrieverModel,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["generative"]);
  const { enqueueSnackbar } = useSnackbar();

  const [selectedGroup, setSelectedGroup] = useState(null);
  const [topK, setTopK] = useState(10);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);
  const [concreteRetrievers, setConcreteRetrievers] = useState([]);
  const [presets, setPresets] = useState([]);
  const [loadError, setLoadError] = useState(null);

  const effectiveTopK = getEffectiveTopK(retrieverModel);

  const presetByKey = useMemo(() => {
    const map = {};
    for (const preset of presets) {
      map[preset.key] = preset;
    }
    return map;
  }, [presets]);

  /**
   * Return the preset recipe matching a retriever model, ignoring top-K at
   * every level, or null if the model is a custom/advanced configuration.
   * @param {object} model - Retriever model config.
   * @returns {object|null} The matching preset or null.
   */
  const presetOf = useCallback(
    (model) => {
      if (!model?.component || !model?.params) return null;
      return (
        presets.find(
          (preset) =>
            preset.component === model.component &&
            deepEqual(
              stripTopKDeep(model.params),
              stripTopKDeep(preset.params),
            ),
        ) || null
      );
    },
    [presets],
  );

  const isAdvanced = useMemo(() => {
    if (!retrieverModel?.component || !retrieverModel?.params) return false;
    return presetOf(retrieverModel) === null;
  }, [retrieverModel, presetOf]);

  const detectSelectedGroup = useCallback(
    (model) => {
      const preset = presetOf(model);
      return preset ? preset.key : null;
    },
    [presetOf],
  );

  // A "leaf" retriever is a simple (non-composite) retriever such as BM25,
  // TF-IDF or DenseEmbeddingRetriever. Composite retrievers (sequential,
  // parallel, MMR reranker, cross-encoder) do not expose a top-K slider,
  // except the default Hybrid preset (a ParallelRetriever) which does.
  const isLeafRetriever = Boolean(
    retrieverModel?.component && !isCompositeKind(retrieverModel.component),
  );
  const sliderMax = Math.max(TOP_K_MAX_DEFAULT, topK);
  const showSlider = isLeafRetriever || selectedGroup === "hybrid";

  useEffect(() => {
    const tk = getEffectiveTopK(retrieverModel);
    if (tk != null) {
      setTopK(Math.max(TOP_K_MIN, tk));
    }
  }, [retrieverModel]);

  useEffect(() => {
    if (loading) return;
    setSelectedGroup(detectSelectedGroup(retrieverModel));
  }, [retrieverModel, loading, detectSelectedGroup]);

  useEffect(() => {
    const load = async () => {
      try {
        await loadRetrieverKinds();
        const retrievers = await getRetrieverComponents("RetrieverModel");
        setConcreteRetrievers(retrievers);
      } catch (error) {
        console.error("Error loading retrievers:", error);
        setLoadError(
          t("generative:rag.validation.modelParamsLoadFailed", {
            model: t("generative:rag.setup.retrieverModel"),
          }),
        );
        enqueueSnackbar(
          t("generative:rag.validation.modelParamsLoadFailed", {
            model: t("generative:rag.setup.retrieverModel"),
          }),
          { variant: "error" },
        );
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // Fetch resolved preset recipes; re-fetch whenever the top-K changes.
  useEffect(() => {
    let cancelled = false;
    getRetrieverPresets(topK)
      .then((data) => {
        if (!cancelled) setPresets(Array.isArray(data) ? data : []);
      })
      .catch((error) => {
        console.error("Error loading retriever presets:", error);
        if (!cancelled) setPresets([]);
        enqueueSnackbar(
          t("generative:rag.validation.modelParamsLoadFailed", {
            model: t("generative:rag.retriever.paradigmLabel"),
          }),
          { variant: "error" },
        );
      });
    return () => {
      cancelled = true;
    };
  }, [topK]);

  // Re-apply the selected preset when recipes refresh (e.g. new top-K).
  useEffect(() => {
    if (loading || isAdvanced || !selectedGroup) return;
    const preset = presetByKey[selectedGroup];
    if (!preset) return;
    const target = { component: preset.component, params: preset.params };
    if (deepEqual(retrieverModel, target)) return;
    setRetrieverModel(target);
  }, [
    presets,
    selectedGroup,
    loading,
    isAdvanced,
    presetByKey,
    retrieverModel,
    setRetrieverModel,
  ]);

  /**
   * Select a retriever preset. If the same preset is already active and not
   * customised, open the advanced modal instead.
   * @param {string} groupKey - "keyword", "semantic", or "hybrid".
   */
  const selectPreset = useCallback(
    (groupKey) => {
      const alreadySelected = !isAdvanced && selectedGroup === groupKey;
      if (alreadySelected) {
        setShowAdvanced(true);
        return;
      }
      if (isAdvanced) {
        setShowAdvanced(true);
        return;
      }
      const preset = presetByKey[groupKey];
      if (!preset) return;
      setShowAdvanced(false);
      setSelectedGroup(groupKey);
      setRetrieverModel({ component: preset.component, params: preset.params });
    },
    [isAdvanced, selectedGroup, presetByKey, setRetrieverModel],
  );

  /**
   * Handle the top-K value change from the slider. The preset recipes are
   * re-fetched with the new value and the selected preset is re-applied by
   * the effects above.
   * @param {object} _event - The slider change event (unused).
   * @param {number} newValue - The new top-K value.
   */
  const handleTopKChange = useCallback(
    (_event, newValue) => {
      const value = Math.max(TOP_K_MIN, newValue);
      setTopK(value);
      // For an advanced (custom) leaf retriever the re-apply effect below is
      // disabled, so update its single top-level top_k directly. Preset leaf
      // retrievers and the Hybrid preset are handled by the preset re-fetch +
      // re-apply flow instead.
      if (isLeafRetriever && isAdvanced && retrieverModel?.component) {
        setRetrieverModel({
          component: retrieverModel.component,
          params: { ...retrieverModel.params, top_k: value },
        });
      }
    },
    [isLeafRetriever, isAdvanced, retrieverModel, setRetrieverModel],
  );

  if (loadError) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        sx={{ minHeight: 120 }}
      >
        <Typography color="error">{loadError}</Typography>
      </Box>
    );
  }

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

  return (
    <RAGSectionColumn>
      <Typography variant="body2" color="textSecondary">
        {t("generative:rag.retriever.description")}
      </Typography>

      <Box
        sx={{
          display: "flex",
          gap: 1,
          alignItems: "stretch",
          flexWrap: "wrap",
        }}
      >
        {presets.map((preset) => (
          <PresetCard
            key={preset.key}
            selected={!isAdvanced && selectedGroup === preset.key}
            onClick={() => selectPreset(preset.key)}
            label={t(PRESET_LABEL_KEYS[preset.key])}
            description={preset.description}
            sx={{ minWidth: 180 }}
          />
        ))}
        {isAdvanced && retrieverModel?.component && (
          <Box
            sx={{
              flex: 1,
              minWidth: 180,
              display: "flex",
              flexDirection: "column",
              gap: 1,
            }}
          >
            <AdvancedConfigCard
              modelName={retrieverModel.component}
              onClick={() => setShowAdvanced(true)}
            />
            {effectiveTopK != null && !isLeafRetriever && (
              <Box
                sx={{
                  border: "1px solid",
                  borderColor: theme.palette.ui.border,
                  borderRadius: 1,
                  backgroundColor: theme.palette.action.selected,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  py: 1.5,
                  px: 1,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ color: theme.palette.text.primary }}
                >
                  {t("generative:rag.retriever.advancedTopK", {
                    topK: effectiveTopK,
                  })}
                </Typography>
              </Box>
            )}
          </Box>
        )}
      </Box>

      {showSlider && (
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("generative:rag.retriever.topKLabel")}
          </Typography>
          <Box sx={{ width: "100%", px: 1 }}>
            <Slider
              value={topK}
              onChange={handleTopKChange}
              min={TOP_K_MIN}
              max={sliderMax}
              step={1}
              marks={[
                { value: 1, label: "1" },
                { value: 5, label: "5" },
                { value: 10, label: "10" },
                { value: 15, label: "15" },
              ]}
              valueLabelDisplay="auto"
              aria-label={t("generative:rag.retriever.topKLabel")}
            />
          </Box>
        </Box>
      )}

      <Button
        variant="contained"
        color="primary"
        size="small"
        onClick={() => setShowAdvanced(true)}
        sx={{
          alignSelf: "flex-start",
          width: "fit-content",
          border: "1px solid",
          borderColor: theme.palette.primary.main,
          backgroundColor: theme.palette.action.selected,
          color: theme.palette.text.primary,
        }}
      >
        ↗ {t("generative:rag.retriever.advancedButton")}
      </Button>

      <RetrieverAdvancedModal
        open={showAdvanced}
        onClose={() => setShowAdvanced(false)}
        selectedParadigm={null}
        allParadigms={concreteRetrievers}
        retrieverModel={retrieverModel}
        setRetrieverModel={setRetrieverModel}
      />
    </RAGSectionColumn>
  );
}

RetrieverSection.propTypes = {
  retrieverModel: PropTypes.object,
  setRetrieverModel: PropTypes.func.isRequired,
};
