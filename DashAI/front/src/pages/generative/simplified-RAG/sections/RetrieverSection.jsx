import { useState, useEffect } from "react";
import {
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Button,
  CircularProgress,
  TextField,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import { getRetrievalParadigm, getRetrieverComponents } from "../../../../api/rag";
import RetrieverAdvancedModal from "../advanced/RetrieverAdvancedModal";

const getDescription = (desc, i18n) => {
  if (!desc) return "";
  if (typeof desc === "string") return desc;
  if (typeof desc === "object" && (desc.en || desc.es)) {
    return desc[i18n.language] || desc.en || desc.es || "";
  }
  return "";
};

const RETRIEVER_EXPLANATIONS = {
  "SparseRetriever": "Best for specific keyword and ID search. Useful for finding exact matches in documents.",
  "DenseRetriever": "Contextual search that understands meaning. Great for finding semantically similar content but may miss specific keywords or IDs.",
  "HybridRetriever": "Combines keyword and contextual search for balanced performance across different query types.",
};

const TOP_K_OPTIONS = [3, 5, 10, 15, 20];

export default function RetrieverSection({
  retrieverModel,
  setRetrieverModel,
}) {
  const { i18n } = useTranslation();
  const [paradigms, setParadigms] = useState([]);
  const [selectedParadigm, setSelectedParadigm] = useState(null);
  const [retrievers, setRetrievers] = useState([]);
  const [selectedRetriever, setSelectedRetriever] = useState(null);
  const [topK, setTopK] = useState(5);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(true);

  // Load paradigms on mount
  useEffect(() => {
    const loadParadigms = async () => {
      try {
        const data = await getRetrievalParadigm();
        setParadigms(data || []);
        if (data && data.length > 0) {
          const defaultParadigm = data.find((p) => p.name === "SparseRetriever") || data[0];
          setSelectedParadigm(defaultParadigm);
        }
      } catch (error) {
        console.error("Error loading retrieval paradigms:", error);
      } finally {
        setLoading(false);
      }
    };
    loadParadigms();
  }, []);

  // Load retrievers when paradigm changes
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
        
        setRetrievers(filtered.length > 0 ? filtered : [selectedParadigm]);
        
        // Try to restore previous selection
        if (retrieverModel?.component) {
          const found = filtered.find((r) => r.name === retrieverModel.component);
          if (found) {
            setSelectedRetriever(found);
          }
        }
      } catch (error) {
        console.error("Error loading retrievers:", error);
        // Fallback: use the paradigm itself as a retriever option
        setRetrievers([selectedParadigm]);
      }
    };

    loadRetrievers();
  }, [selectedParadigm]);


  const handleParadigmChange = (event, newValue) => {
    if (newValue !== null) {
      const selected = paradigms.find((p) => p.name === newValue);
      setSelectedParadigm(selected);
      setSelectedRetriever(null);
      if (selected) {
        // Reset retriever model when paradigm changes
        setRetrieverModel({
          component: "",
          params: { top_k: topK },
        });
      }
    }
  };

  const handleRetrieverChange = (event, newValue) => {
    if (newValue !== null) {
      const selected = retrievers.find((r) => r.name === newValue);
      setSelectedRetriever(selected);
      if (selected) {
        setRetrieverModel({
          component: selected.name,
          params: { top_k: topK },
        });
      }
    }
  };

  const handleTopKChange = (newValue) => {
    const value = parseInt(newValue);
    if (!isNaN(value) && value > 0) {
      setTopK(value);
      if (selectedParadigm) {
        setRetrieverModel((prev) => ({
          ...prev,
          params: { ...prev.params, top_k: value },
        }));
      }
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
          Select your retrieval paradigm. The retriever will search through your documents
          and return the most relevant chunks.
        </Typography>

        {/* Paradigm Selection with Toggle Buttons */}
        <Box>
          <Typography variant="body2" sx={{ mb: 2, fontWeight: 500 }}>
            Retrieval Paradigm
          </Typography>
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
                  <Typography variant="subtitle2">{paradigm.name}</Typography>
                  <Typography variant="caption">
                    {RETRIEVER_EXPLANATIONS[paradigm.name] || "Custom retriever"}
                  </Typography>
                </Box>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>

        {/* Selected Configuration Info */}
        {selectedParadigm && (
          <Box display="flex" flexDirection="column" gap={2}>
            {/* Top K Selector */}
            <Box>
              <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                Number of Results (Top K)
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
                      "&.Mui-selected": {
                        backgroundColor: "primary.main",
                        color: "primary.contrastText",
                        borderColor: "primary.main",
                        "&:hover": {
                          backgroundColor: "secondary.dark",
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
