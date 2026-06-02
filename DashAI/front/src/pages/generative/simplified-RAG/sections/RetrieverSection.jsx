import { useState, useEffect, useMemo, useCallback } from "react";
import {
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
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

const TOP_K_OPTIONS = [3, 5, 10, 15, 20];

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
  return typeof model.params.top_k === "number" ? model.params.top_k : null;
}

function buildHybridModel(effectiveK, defaults = {}) {
  const tfidf = defaults.tfidf || {};
  const hf = defaults.huggingface || {};
  return {
    component: "ParallelRetriever",
    params: {
      merge_strategy: "round_robin",
      children: [
        {
          component: "TFIDFRetriever",
          params: { ...tfidf, top_k: Math.max(1, Math.ceil(effectiveK / 2)) },
        },
        {
          component: "HuggingFaceDenseRetriever",
          params: { ...hf, top_k: Math.max(1, Math.floor(effectiveK / 2)) },
        },
      ],
    },
  };
}

const API_GROUPS = {
  keyword: "SparseRetriever",
  embedding: "DenseRetriever",
};

export default function RetrieverSection({
  retrieverModel,
  setRetrieverModel,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["generative"]);

  const [groups, setGroups] = useState([]);
  const [allRetrievers, setAllRetrievers] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [topK, setTopK] = useState(retrieverModel?.params?.top_k || 10);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);
  const [hybridDefaults, setHybridDefaults] = useState({ tfidf: null, huggingface: null });
  const [defaultsMap, setDefaultsMap] = useState({});

  const effectiveTopK = getEffectiveTopK(retrieverModel);

  useEffect(() => {
    const tk = getEffectiveTopK(retrieverModel);
    if (tk != null) {
      setTopK(tk);
    }
  }, [retrieverModel]);

  const isAdvanced = useMemo(() => {
    if (!retrieverModel?.params || !retrieverModel?.component || !selectedGroup) return false;

    const tk = getEffectiveTopK(retrieverModel);
    if (tk == null || !TOP_K_OPTIONS.includes(tk)) return true;

    if (selectedGroup === "hybrid") {
      if (retrieverModel.component !== "ParallelRetriever") return true;
      const tk = getEffectiveTopK(retrieverModel);
      if (tk == null || !TOP_K_OPTIONS.includes(tk)) return true;
      const def = buildHybridModel(tk, hybridDefaults);
      return !deepEqual(retrieverModel.params, def.params);
    }

    const group = groups.find((g) => g.key === selectedGroup);
    if (!group) return true;
    const matchedMember = group.members.find(
      (m) => m.name === retrieverModel.component,
    );
    if (!matchedMember) return true;
    const defaultParams = defaultsMap[matchedMember.name] || {};
    const filterTopK = (obj) =>
      Object.fromEntries(
        Object.entries(obj || {}).filter(([k]) => k !== "top_k"),
      );
    return !deepEqual(
      filterTopK(retrieverModel.params),
      filterTopK(defaultParams),
    );
  }, [retrieverModel, selectedGroup, groups, hybridDefaults, defaultsMap]);

  useEffect(() => {
    const load = async () => {
      try {
        const groupResults = [];
        const allRet = [];

        for (const [key, parentName] of Object.entries(API_GROUPS)) {
          const children = await getRetrieverComponents(parentName);
          if (children.length > 0) {
            groupResults.push({ key, members: children });
            allRet.push(...children);
          }
        }

        groupResults.push({ key: "hybrid", members: [] });
        allRet.push({ name: "ParallelRetriever" });

        setGroups(groupResults);
        setAllRetrievers(allRet);

        const dm = {};
        for (const ret of allRet) {
          if (ret.name !== "ParallelRetriever") {
            dm[ret.name] = await resolveDefaults(ret.name);
          }
        }
        setDefaultsMap(dm);

        const tfidfDefaults = dm["TFIDFRetriever"] || {};
        const hfDefaults = dm["HuggingFaceDenseRetriever"] || {};
        setHybridDefaults({ tfidf: tfidfDefaults, huggingface: hfDefaults });

        if (
          retrieverModel?.component === "ParallelRetriever" &&
          Object.keys(tfidfDefaults).length > 0 &&
          Object.keys(hfDefaults).length > 0
        ) {
          setRetrieverModel(
            buildHybridModel(getEffectiveTopK(retrieverModel), {
              tfidf: tfidfDefaults,
              huggingface: hfDefaults,
            }),
          );
        }

        if (retrieverModel?.component) {
          const found = allRet.find((r) => r.name === retrieverModel.component);
          if (found) {
            setSelectedModel(found === groupResults[2] ? "hybrid" : found);
            const grp = groupResults.find(
              (g) => g.members.some((m) => m.name === retrieverModel.component) ||
                (retrieverModel.component === "ParallelRetriever" && g.key === "hybrid"),
            );
            if (grp) setSelectedGroup(grp.key);
          }
        }
      } catch (error) {
        console.error("Error loading retrievers:", error);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const selectGroup = async (groupKey) => {
    const alreadySelected = !isAdvanced && selectedGroup === groupKey;
    if (alreadySelected) {
      setShowAdvanced(true);
      return;
    }

    setShowAdvanced(false);
    setSelectedGroup(groupKey);
    if (groupKey === "hybrid") {
      setSelectedModel({ name: "ParallelRetriever" });
      setRetrieverModel(buildHybridModel(topK, hybridDefaults));
      return;
    }
    const group = groups.find((g) => g.key === groupKey);
    if (group && group.members.length > 0) {
      const model = group.members[0];
      setSelectedModel(model);
      const defaults = await resolveDefaults(model.name);
      setRetrieverModel({
        component: model.name,
        params: { ...defaults, top_k: topK },
      });
    }
  };

  const handleTopKChange = useCallback((newValue) => {
    const value = parseInt(newValue);
    if (!isNaN(value) && value > 0) {
      if (isAdvanced) return;
      setTopK(value);
      if (selectedGroup === "hybrid") {
        setRetrieverModel(buildHybridModel(value, hybridDefaults));
      } else {
        setRetrieverModel((prev) => ({
          ...prev,
          params: { ...(prev?.params || {}), top_k: value },
        }));
      }
    }
  }, [isAdvanced, selectedGroup, setRetrieverModel, hybridDefaults]);

  const getGroupLabel = (key) => {
    switch (key) {
      case "keyword": return t("generative:simplifiedRag.composite.keywordGroup");
      case "embedding": return t("generative:simplifiedRag.composite.embeddingGroup");
      case "hybrid": return t("generative:simplifiedRag.composite.hybridGroup");
      default: return key;
    }
  };

  const getGroupDescription = (key) => {
    if (key === "hybrid") return t("generative:simplifiedRag.composite.hybridDescription");
    const group = groups.find((g) => g.key === key);
    if (!group) return "";
    return group.members.map((r) => {
      const dn = r.display_name;
      if (!dn) return r.name;
      if (typeof dn === "string") return dn;
      return dn.en || r.name;
    }).join(", ");
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
          {t("generative:simplifiedRag.retriever.description")}
        </Typography>

        <Box>
          <Typography variant="body2" sx={{ fontWeight: 500, mb: 2 }}>
            {t("generative:simplifiedRag.retriever.paradigmLabel")}
          </Typography>
          <Box sx={{ display: "flex", gap: 1, alignItems: "stretch", flexWrap: "wrap" }}>
            {groups.map((group) => (
              <PresetCard
                key={group.key}
                selected={!isAdvanced && selectedGroup === group.key}
                onClick={() => selectGroup(group.key)}
                label={getGroupLabel(group.key)}
                description={getGroupDescription(group.key)}
                sx={{ flex: 1, minWidth: 180, py: 2, px: 1 }}
              />
            ))}
            {isAdvanced && retrieverModel?.component && (
              <Box sx={{ flex: 1, minWidth: 180, display: "flex", flexDirection: "column", gap: 1 }}>
                <AdvancedConfigCard
                  modelName={retrieverModel.component}
                  onClick={() => setShowAdvanced(true)}
                />
                {effectiveTopK != null && (
                  <Box
                    sx={{
                      border: "1px solid",
                      borderColor: theme.palette.accent.amberBorder,
                      borderRadius: 1,
                      backgroundColor: theme.palette.accent.amberDim,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      py: 1.5,
                      px: 1,
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{ color: theme.palette.primary.main, fontWeight: 500 }}
                    >
                      Advanced Top K: {effectiveTopK}
                    </Typography>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        </Box>

        {selectedGroup && (
          <Box>
            {!isAdvanced && (
              <>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  {t("generative:simplifiedRag.retriever.topKLabel")}
                </Typography>
                <ToggleButtonGroup
                  value={String(topK)}
                  exclusive
                  onChange={(_event, newValue) => {
                    if (newValue !== null) {
                      handleTopKChange(newValue);
                    }
                  }}
                  fullWidth
                  sx={{ display: "flex", gap: 1 }}
                >
                  {TOP_K_OPTIONS.map((k) => (
                    <ToggleButton
                      key={k}
                      value={String(k)}
                      sx={{
                        flex: 1,
                        py: 1.5,
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
                      <Typography variant="body2">{k}</Typography>
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
              </>
            )}
          </Box>
        )}

        <Button
          variant="outlined"
          color="primary"
          onClick={() => setShowAdvanced(true)}
          fullWidth
        >
          ↗ {t("generative:simplifiedRag.retriever.advancedButton")}
        </Button>
      </Box>

      <RetrieverAdvancedModal
        open={showAdvanced}
        onClose={() => setShowAdvanced(false)}
        selectedParadigm={selectedModel}
        allParadigms={allRetrievers}
        retrieverModel={retrieverModel}
        setRetrieverModel={setRetrieverModel}
      />
    </>
  );
}

RetrieverSection.propTypes = {
  retrieverModel: PropTypes.object,
  setRetrieverModel: PropTypes.func.isRequired,
};
