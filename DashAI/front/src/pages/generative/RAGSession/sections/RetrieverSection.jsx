import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  useTheme,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getRetrieverComponents } from "../../../../api/rag";
import { resolveDefaults } from "../../../../utils/schema";
import RetrieverAdvancedModal from "../advanced/RetrieverAdvancedModal";
import AdvancedConfigCard from "../components/AdvancedConfigCard";
import PresetCard from "../components/PresetCard";
import RAGSectionColumn from "../components/RAGSectionColumn";

const TOP_K_OPTIONS = [3, 5, 10, 15, 20];

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
 * Omits `top_k` key from an object for purpose of comparing
 * retriever configurations while ignoring the top-K value.
 */
const omitTopK = (obj) =>
  Object.fromEntries(Object.entries(obj || {}).filter(([k]) => k !== "top_k"));

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
 * Build a BM25 keyword retriever configuration.
 * @param {object} bm25Defaults - Default BM25 params.
 * @param {number} topK         - Number of top results.
 * @returns {object} Model config { component, params }.
 */
function buildKeywordModel(bm25Defaults, topK) {
  return {
    component: "BM25Retriever",
    params: { ...bm25Defaults, top_k: topK },
  };
}

/**
 * Build a DenseEmbedding (semantic) retriever configuration using SentenceTransformer.
 * @param {object} embeddingDefaults  - Default embedding model params.
 * @param {object} retrieverDefaults  - Default dense retriever params.
 * @param {number} topK               - Number of top results.
 * @returns {object} Model config { component, params }.
 */
function buildSemanticModel(embeddingDefaults, retrieverDefaults, topK) {
  return {
    component: "DenseEmbeddingRetriever",
    params: {
      embedding_model: {
        component: "SentenceTransformerEmbedding",
        params: {
          ...embeddingDefaults,
          model_name: "microsoft/harrier-oss-v1-0.6b",
        },
      },
      similarity_metric: retrieverDefaults.similarity_metric || "cosine",
      top_k: topK,
    },
  };
}

/**
 * Build a hybrid (Parallel) retriever configuration with BM25 + DenseEmbedding.
 * @param {object} bm25Defaults       - Default BM25 params.
 * @param {object} embeddingDefaults  - Default embedding model params.
 * @param {object} retrieverDefaults  - Default dense retriever params.
 * @param {number} topK               - Total top-K split across sub-retrievers.
 * @returns {object} Model config { component, params }.
 */
function buildHybridModel(
  bm25Defaults,
  embeddingDefaults,
  retrieverDefaults,
  topK,
) {
  const kwTopK = Math.ceil(topK / 2);
  const seTopK = Math.floor(topK / 2);
  return {
    component: "ParallelRetriever",
    params: {
      merge_strategy: "round_robin",
      children: [
        {
          component: "BM25Retriever",
          params: { ...bm25Defaults, top_k: kwTopK },
        },
        {
          component: "DenseEmbeddingRetriever",
          params: {
            embedding_model: {
              component: "SentenceTransformerEmbedding",
              params: {
                ...embeddingDefaults,
                model_name: "microsoft/harrier-oss-v1-0.6b",
              },
            },
            similarity_metric: retrieverDefaults.similarity_metric || "cosine",
            top_k: seTopK,
          },
        },
      ],
    },
  };
}

/**
 * Retriever model selection section.
 * Provides keyword / semantic / hybrid presets, top-K picker,
 * and an advanced configuration modal for custom retrievers.
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

  const [selectedGroup, setSelectedGroup] = useState(null);
  const [topK, setTopK] = useState(10);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);
  const [concreteRetrievers, setConcreteRetrievers] = useState([]);
  const [bm25Defaults, setBm25Defaults] = useState({});
  const [embeddingDefaults, setEmbeddingDefaults] = useState({});
  const [denseRetrieverDefaults, setDenseRetrieverDefaults] = useState({});

  const effectiveTopK = getEffectiveTopK(retrieverModel);

  const keywordModel = useMemo(
    () => buildKeywordModel(bm25Defaults, effectiveTopK || topK),
    [bm25Defaults, effectiveTopK, topK],
  );

  const semanticModel = useMemo(
    () =>
      buildSemanticModel(
        embeddingDefaults,
        denseRetrieverDefaults,
        effectiveTopK || topK,
      ),
    [embeddingDefaults, denseRetrieverDefaults, effectiveTopK, topK],
  );

  const hybridModel = useMemo(
    () =>
      buildHybridModel(
        bm25Defaults,
        embeddingDefaults,
        denseRetrieverDefaults,
        effectiveTopK || topK,
      ),
    [
      bm25Defaults,
      embeddingDefaults,
      denseRetrieverDefaults,
      effectiveTopK,
      topK,
    ],
  );

  const isAdvanced = useMemo(() => {
    if (!retrieverModel?.component || !retrieverModel?.params) return false;

    const modelNoTopK = {
      component: retrieverModel.component,
      params: omitTopK(retrieverModel.params),
    };

    const kwNoTopK = {
      component: keywordModel.component,
      params: omitTopK(keywordModel.params),
    };

    const seNoTopK = {
      component: semanticModel.component,
      params: omitTopK(semanticModel.params),
    };

    const hyNoTopK = {
      component: hybridModel.component,
      params: omitTopK(hybridModel.params),
    };

    return (
      !deepEqual(modelNoTopK, kwNoTopK) &&
      !deepEqual(modelNoTopK, seNoTopK) &&
      !deepEqual(modelNoTopK, hyNoTopK)
    );
  }, [retrieverModel, keywordModel, semanticModel, hybridModel]);

  /**
   * Determine which preset group (keyword / semantic / hybrid / null) the
   * current model configuration matches, ignoring the top-K value.
   * @param {object} model - Retriever model config.
   * @returns {string|null} Group key or null for custom configs.
   */
  const detectSelectedGroup = useCallback(
    (model) => {
      if (!model?.component) return null;

      const modelNoTopK = {
        component: model.component,
        params: omitTopK(model.params),
      };

      if (
        deepEqual(modelNoTopK, {
          component: keywordModel.component,
          params: omitTopK(keywordModel.params),
        })
      ) {
        return "keyword";
      }
      if (
        deepEqual(modelNoTopK, {
          component: semanticModel.component,
          params: omitTopK(semanticModel.params),
        })
      ) {
        return "semantic";
      }
      if (
        deepEqual(modelNoTopK, {
          component: hybridModel.component,
          params: omitTopK(hybridModel.params),
        })
      ) {
        return "hybrid";
      }
      return null;
    },
    [keywordModel, semanticModel, hybridModel],
  );

  useEffect(() => {
    const tk = getEffectiveTopK(retrieverModel);
    if (tk != null) {
      setTopK(tk);
    }
  }, [retrieverModel]);

  useEffect(() => {
    if (loading) return;
    const group = detectSelectedGroup(retrieverModel);
    setSelectedGroup(group);
  }, [retrieverModel, loading, detectSelectedGroup]);

  useEffect(() => {
    const load = async () => {
      try {
        const allRetrieversRaw = await getRetrieverComponents("RetrieverModel");
        const retrievers = allRetrieversRaw.filter(
          (c) => !(c.flags || []).includes("abstract"),
        );
        setConcreteRetrievers(retrievers);

        const [bm25, embeddingDefaultsRes, denseRetriever] = await Promise.all([
          resolveDefaults("BM25Retriever").catch(() => ({})),
          resolveDefaults("SentenceTransformerEmbedding").catch(() => ({})),
          resolveDefaults("DenseEmbeddingRetriever").catch(() => ({})),
        ]);

        setBm25Defaults(bm25);
        setEmbeddingDefaults(embeddingDefaultsRes);
        setDenseRetrieverDefaults(denseRetriever);
      } catch (error) {
        console.error("Error loading retrievers:", error);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

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

      setShowAdvanced(false);
      setSelectedGroup(groupKey);

      if (groupKey === "keyword") {
        setRetrieverModel(keywordModel);
      } else if (groupKey === "semantic") {
        setRetrieverModel(semanticModel);
      } else if (groupKey === "hybrid") {
        setRetrieverModel(hybridModel);
      }
    },
    [
      isAdvanced,
      selectedGroup,
      keywordModel,
      semanticModel,
      hybridModel,
      setRetrieverModel,
    ],
  );

  /**
   * Handle the top-K value change and rebuild the selected preset with the new value.
   * @param {string} newValue - The new top-K value as a string.
   */
  const handleTopKChange = useCallback(
    (newValue) => {
      const value = parseInt(newValue);
      if (isNaN(value) || value <= 0 || isAdvanced) return;
      setTopK(value);

      if (selectedGroup === "keyword") {
        setRetrieverModel(buildKeywordModel(bm25Defaults, value));
      } else if (selectedGroup === "semantic") {
        setRetrieverModel(
          buildSemanticModel(embeddingDefaults, denseRetrieverDefaults, value),
        );
      } else if (selectedGroup === "hybrid") {
        setRetrieverModel(
          buildHybridModel(
            bm25Defaults,
            embeddingDefaults,
            denseRetrieverDefaults,
            value,
          ),
        );
      }
    },
    [
      isAdvanced,
      selectedGroup,
      bm25Defaults,
      embeddingDefaults,
      denseRetrieverDefaults,
      setRetrieverModel,
    ],
  );

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
        <PresetCard
          key="keyword"
          selected={!isAdvanced && selectedGroup === "keyword"}
          onClick={() => selectPreset("keyword")}
          label={t("generative:rag.retriever.keywordLabel")}
          description="BM25"
          sx={{ minWidth: 180 }}
        />
        <PresetCard
          key="semantic"
          selected={!isAdvanced && selectedGroup === "semantic"}
          onClick={() => selectPreset("semantic")}
          label={t("generative:rag.retriever.semanticLabel")}
          description="Harrier OSS v1 0.6B"
          sx={{ minWidth: 180 }}
        />
        <PresetCard
          key="hybrid"
          selected={!isAdvanced && selectedGroup === "hybrid"}
          onClick={() => selectPreset("hybrid")}
          label={t("generative:rag.retriever.hybridLabel")}
          description={t("generative:rag.retriever.hybridDescription")}
          sx={{ minWidth: 180 }}
        />
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
            {effectiveTopK != null && (
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

      {selectedGroup && (
        <Box>
          {!isAdvanced && (
            <>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                {t("generative:rag.retriever.topKLabel")}
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  gap: 1,
                  alignItems: "stretch",
                  flexWrap: "wrap",
                  width: "100%",
                }}
              >
                {TOP_K_OPTIONS.map((k) => (
                  <PresetCard
                    key={k}
                    selected={topK === k}
                    onClick={() => handleTopKChange(String(k))}
                    label={String(k)}
                    description={""}
                    sx={{
                      flex: "1 1 0",
                      minWidth: 0,
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  />
                ))}
              </Box>
            </>
          )}
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
