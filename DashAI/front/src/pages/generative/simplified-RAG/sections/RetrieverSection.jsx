import { useState, useEffect, useMemo } from "react";
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
import { getRetrievalParadigm, getRetrieverComponents } from "../../../../api/rag";
import { buildDefaultValuesFromSchemaProperties } from "../components/ragFormDefaults";
import RetrieverAdvancedModal from "../advanced/RetrieverAdvancedModal";

const TOP_K_OPTIONS = [3, 5, 10, 15, 20];

export default function RetrieverSection({
  retrieverModel,
  setRetrieverModel,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["generative"]);

  const formatParadigmName = (name) => {
    if (!name) return "";
    const withSpaces = name.replace(/([A-Z])/g, " $1").trim();
    return withSpaces.charAt(0).toUpperCase() + withSpaces.slice(1).toLowerCase();
  };
  
  const [paradigms, setParadigms] = useState([]);
  const [selectedParadigm, setSelectedParadigm] = useState(null);
  const [retrievers, setRetrievers] = useState([]);
  const [selectedRetriever, setSelectedRetriever] = useState(null);
  const [topK, setTopK] = useState(retrieverModel?.params?.top_k || 5);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (retrieverModel?.params?.top_k && retrieverModel.params.top_k !== topK) {
      setTopK(retrieverModel.params.top_k);
    }
  }, [retrieverModel?.params?.top_k]);

  const isAdvanced = useMemo(() => {
    if (!selectedRetriever || !retrieverModel?.params) return false;
    
    const defaultParams = buildDefaultValuesFromSchemaProperties(selectedRetriever.schema?.properties || {});
    
    return Object.keys(retrieverModel.params).some(key => {
      if (key === 'top_k') return false;
      return JSON.stringify(retrieverModel.params[key]) !== JSON.stringify(defaultParams[key]);
    });
  }, [selectedRetriever, retrieverModel?.params]);

  useEffect(() => {
    const loadParadigms = async () => {
      try {
        const data = await getRetrievalParadigm();
        setParadigms(data || []);
        if (data && data.length > 0) {
          if (retrieverModel?.component) {
            setSelectedParadigm(data.find(p => p.name === "SparseRetriever") || data[0]);
          } else {
            const defaultParadigm = data.find((p) => p.name === "SparseRetriever") || data[0];
            setSelectedParadigm(defaultParadigm);
          }
        }
      } catch (error) {
        console.error("Error loading retrieval paradigms:", error);
      } finally {
        setLoading(false);
      }
    };
    loadParadigms();
  }, []);

  useEffect(() => {
    if (!selectedParadigm) {
      setRetrievers([]);
      setSelectedRetriever(null);
      return;
    }

    const loadRetrievers = async () => {
      try {
        const data = await getRetrieverComponents(selectedParadigm.name);
        const filtered = data?.filter(
          (r) =>
            r?.name !== selectedParadigm.name &&
            r?.configurable_object !== false
        ) || [];
        
        const availableRetrievers = filtered.length > 0 ? filtered : [selectedParadigm];
        setRetrievers(availableRetrievers);
        
        if (retrieverModel?.component) {
          const found = availableRetrievers.find((r) => r.name === retrieverModel.component);
          if (found) {
            setSelectedRetriever(found);
            if (retrieverModel.params?.top_k) {
              setTopK(retrieverModel.params.top_k);
            }
          } else {
            selectDefaultRetriever(availableRetrievers);
          }
        } else {
          selectDefaultRetriever(availableRetrievers);
        }
      } catch (error) {
        console.error("Error loading retrievers:", error);
        setRetrievers([selectedParadigm]);
      }
    };

    loadRetrievers();
  }, [selectedParadigm]);

  const selectDefaultRetriever = (availableRetrievers) => {
    const defaultRetriever = availableRetrievers[0];
    setSelectedRetriever(defaultRetriever);
    setRetrieverModel({
      component: defaultRetriever.name,
      params: { ...buildDefaultValuesFromSchemaProperties(defaultRetriever.schema?.properties || {}), top_k: topK },
    });
  };

  const handleParadigmChange = (event, newValue) => {
    if (newValue !== null) {
      const selected = paradigms.find((p) => p.name === newValue);
      setSelectedParadigm(selected);
      setSelectedRetriever(null);
    }
  };

  const handleTopKChange = (newValue) => {
  const value = parseInt(newValue);
  if (!isNaN(value) && value > 0) {
    setTopK(value);
    setRetrieverModel({
      ...retrieverModel,
      params: {
        ...(retrieverModel?.params || {}),
        top_k: value,
      },
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
          {t("generative:simplifiedRag.retriever.description")}
        </Typography>

        {/* Paradigm Selection */}
        <Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {t("generative:simplifiedRag.retriever.paradigmLabel")}
            </Typography>
            {isAdvanced && (
              <Typography variant="caption" sx={{ color: "warning.main", fontWeight: "bold" }}>
                {t("generative:simplifiedRag.retriever.advancedApplied")}
              </Typography>
            )}
          </Box>
          <ToggleButtonGroup
            value={selectedParadigm?.name || ""}
            exclusive
            onChange={handleParadigmChange}
            fullWidth
            sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}
          >
            {paradigms.map((paradigm) => (
              <ToggleButton
                key={paradigm.name}
                value={paradigm.name}
                sx={{
                  flex: 1,
                  minWidth: 200,
                  py: 2,
                  px: 1,
                  textTransform: "none",
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
                  <Typography variant="subtitle2" sx={{ textAlign: "center" }}>
                    {formatParadigmName(paradigm.name)}
                  </Typography>
                  <Typography variant="caption" sx={{ textAlign: "left" }}>
                    {t(`generative:simplifiedRag.retriever.explanations.${paradigm.name}`, { defaultValue: "Custom retriever" })}
                  </Typography>
                </Box>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>

        {selectedParadigm && (
          <Box display="flex" flexDirection="column" gap={2}>
            <Box>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                {t("generative:simplifiedRag.retriever.topKLabel")}
              </Typography>
              <ToggleButtonGroup
                value={String(topK)}
                exclusive
                onChange={(event, newValue) => {
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
            </Box>
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
        selectedParadigm={selectedParadigm}
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
