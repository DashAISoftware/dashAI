import { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  CircularProgress,
  Collapse,
  IconButton,
  LinearProgress,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import EditIcon from "@mui/icons-material/Edit";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import SideBar from "../../threeSectionLayout/panelContainers/SideBar";
import PresetCardList from "./PresetCardList";
import PromptEditor from "./PromptEditor";
import GeneratorPicker from "./GeneratorPicker";
import ChunkingAdvancedModal from "../../../pages/generative/RAGSession/advanced/ChunkingAdvancedModal";
import RetrieverAdvancedModal from "../../../pages/generative/RAGSession/advanced/RetrieverAdvancedModal";
import { loadRetrieverKinds } from "../../../pages/generative/RAGSession/retrieverKinds";
import {
  getChunkingPresets,
  getRAGSession,
  getRetrieverComponents,
  getRetrieverPresets,
  getSessionConfiguration,
  updateGenerativeSessionParams,
} from "../../../api/rag";
import { updateGenerativeSession } from "../../../api/session";
import { getRequiredDownloads } from "../../../api/component";
import { subscribeAnyDownloadState } from "../../models/model/ComponentDownloadControl";
import { getApiErrorMessage } from "../../../utils/apiError";

/**
 * Section keys, matching the RAG parameter keys the backend uses, in the order
 * the pipeline applies them: split the documents, retrieve from them, answer
 * with a model, phrase it with a prompt.
 */
const SECTIONS = [
  "chunking_model",
  "retriever_model",
  "generation_model",
  "prompt",
];

/**
 * The single place a RAG session is configured.
 *
 * Replaces the split between a read-only summary in the centre and an editable
 * params bar on the right: every component appears once, under one name, and is
 * editable here. All labels, preset names and the context budget are resolved
 * by the backend, so this component renders rather than translates.
 *
 * @param {object}   props
 * @param {number}   props.sessionId - The RAG session being configured.
 * @param {object}   [props.indexStatus] - Current indexing state, for the
 *   progress, re-indexing and failure notices.
 * @param {Function} [props.onSaved] - Called after parameters are persisted.
 * @param {Function} [props.onRetryIndexing] - Called to restart a failed index.
 * @param {Function} [props.onSessionRenamed] - Called with the new name.
 * @param {Function} [props.onGeneratorChange] - Called with the generator
 *   selected in the draft, saved or not, so the chat can gate on it.
 * @returns {JSX.Element} The configuration panel.
 */
export default function RAGConfigPanel({
  sessionId,
  indexStatus,
  onSaved,
  onRetryIndexing,
  onSessionRenamed,
  onGeneratorChange,
}) {
  const { t, i18n } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();

  const [configuration, setConfiguration] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [expandedSection, setExpandedSection] = useState(SECTIONS[0]);
  const [promptValid, setPromptValid] = useState(true);

  // Editable working copy of the parameters, seeded from the session.
  const [draft, setDraft] = useState(null);
  const [savedDraft, setSavedDraft] = useState(null);
  const [modelAvailable, setModelAvailable] = useState(true);

  const [chunkingPresets, setChunkingPresets] = useState([]);
  const [retrieverPresets, setRetrieverPresets] = useState([]);
  const [retrieverComponents, setRetrieverComponents] = useState([]);
  const [showChunkingAdvanced, setShowChunkingAdvanced] = useState(false);
  const [showRetrieverAdvanced, setShowRetrieverAdvanced] = useState(false);

  const [editingMetadata, setEditingMetadata] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const load = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      const [session, resolved] = await Promise.all([
        getRAGSession(sessionId),
        getSessionConfiguration(sessionId),
      ]);
      const parameters = session.parameters || {};
      const next = {
        chunking_model: parameters.chunking_model || {
          component: "",
          params: {},
        },
        retriever_model: parameters.retriever_model || {
          component: "",
          params: {},
        },
        prompt: parameters.prompt || { component: "", params: {} },
        generation_model: parameters.generation_model || {
          component: "",
          params: {},
        },
      };
      setDraft(next);
      setSavedDraft(next);
      setConfiguration(resolved);
      setName(session.name || "");
      setDescription(session.description || "");
    } catch (error) {
      console.error("Failed to load RAG configuration:", error);
      enqueueSnackbar(t("generative:rag.paramsPanel.failedToLoad"), {
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  }, [sessionId, enqueueSnackbar, t]);

  useEffect(() => {
    load();
  }, [load]);

  // Preset recipes come resolved from the backend; the Top-K currently in use
  // keeps the retriever recipes comparable with what the session already has.
  useEffect(() => {
    getChunkingPresets()
      .then(setChunkingPresets)
      .catch((error) =>
        console.error("Failed to load chunking presets:", error),
      );
  }, []);

  // The advanced retriever builder needs the full component list, and its
  // grouping needs the retriever taxonomy the backend exposes.
  useEffect(() => {
    loadRetrieverKinds()
      .then(() => getRetrieverComponents("BaseRetriever"))
      .then(setRetrieverComponents)
      .catch((error) =>
        console.error("Failed to load retriever components:", error),
      );
  }, []);

  const topK = configuration?.retriever_model?.top_k;
  useEffect(() => {
    getRetrieverPresets(topK || 10)
      .then(setRetrieverPresets)
      .catch((error) =>
        console.error("Failed to load retriever presets:", error),
      );
  }, [topK]);

  const generatorName = draft?.generation_model?.component;
  useEffect(() => {
    if (generatorName !== undefined) onGeneratorChange?.(generatorName);
  }, [generatorName, onGeneratorChange]);

  const retrieverKey = JSON.stringify(draft?.retriever_model ?? null);
  const [missingRetrieverDownloads, setMissingRetrieverDownloads] = useState(
    [],
  );
  useEffect(() => {
    const retrieverModel = JSON.parse(retrieverKey);
    if (!retrieverModel?.component) {
      setMissingRetrieverDownloads([]);
      return undefined;
    }
    let cancelled = false;
    const check = () =>
      getRequiredDownloads({ retriever_model: retrieverModel })
        .then((missing) => {
          if (!cancelled) setMissingRetrieverDownloads(missing);
        })
        .catch(() => {
          if (!cancelled) setMissingRetrieverDownloads([]);
        });
    const timer = setTimeout(check, 300);
    const unsubscribe = subscribeAnyDownloadState(() => check());
    return () => {
      cancelled = true;
      clearTimeout(timer);
      unsubscribe();
    };
  }, [retrieverKey]);
  const retrieverDownloadMessage =
    missingRetrieverDownloads.length > 0
      ? t("common:componentDownload.mustDownloadNested", {
          names: missingRetrieverDownloads
            .map((missing) => missing.display_name || missing.name)
            .join(", "),
        })
      : null;

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(savedDraft),
    [draft, savedDraft],
  );

  // Which sections hold unsaved edits. One Save still sends the whole draft --
  // the endpoint replaces every parameter at once -- but with the sections
  // behind tabs a pending change is otherwise invisible from another tab.
  const dirtySections = useMemo(() => {
    if (!draft || !savedDraft) return [];
    return SECTIONS.filter(
      (key) => JSON.stringify(draft[key]) !== JSON.stringify(savedDraft[key]),
    );
  }, [draft, savedDraft]);

  const updateSection = useCallback((key, value) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSave = async () => {
    if (!dirty || saving) return;
    setSaving(true);
    try {
      await updateGenerativeSessionParams(sessionId, draft);
      setSavedDraft(draft);
      const resolved = await getSessionConfiguration(sessionId);
      setConfiguration(resolved);
      enqueueSnackbar(t("generative:rag.paramsPanel.updated"), {
        variant: "success",
      });
      onSaved?.();
    } catch (error) {
      console.error("Failed to update RAG session:", error);
      enqueueSnackbar(
        getApiErrorMessage(
          error,
          t("generative:rag.paramsPanel.failedToUpdate"),
        ),
        { variant: "error" },
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = () => setDraft(savedDraft);

  const handleSaveMetadata = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      enqueueSnackbar(t("generative:rag.validation.nameRequired"), {
        variant: "error",
      });
      return;
    }
    try {
      await updateGenerativeSession({
        id: String(sessionId),
        formData: { name: trimmed, description },
      });
      setEditingMetadata(false);
      onSessionRenamed?.(trimmed);
      enqueueSnackbar(t("generative:rag.summary.sessionUpdated"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to update session metadata:", error);
      enqueueSnackbar(t("generative:rag.summary.failedToUpdateSession"), {
        variant: "error",
      });
    }
  };

  if (loading || !configuration || !draft) {
    return (
      <SideBar>
        <Box
          sx={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <CircularProgress size={32} />
        </Box>
      </SideBar>
    );
  }

  const budget = configuration.context_budget;
  const budgetUsed =
    budget.context_window > 0
      ? Math.min(
          100,
          Math.round(
            ((budget.context_window - budget.available) /
              budget.context_window) *
              100,
          ),
        )
      : 0;

  /**
   * The preset recipe the unsaved draft currently matches, if any.
   *
   * Clicking a chip applies that recipe verbatim, so an exact comparison
   * against the recipe is enough to keep the panel in step with the draft — no
   * waiting for a save round-trip, and no domain knowledge here.
   *
   * @param {string} key - The configuration section key.
   * @param {Array} presets - The preset recipes for that section.
   * @returns {object|null} The matching recipe, or null for a custom config.
   */
  const matchedPreset = (key, presets) => {
    const ref = draft[key];
    return (
      presets.find(
        (preset) =>
          preset.component === ref?.component &&
          JSON.stringify(preset.params) === JSON.stringify(ref?.params),
      ) ?? null
    );
  };

  /**
   * Which preset key is active for a section.
   * @param {string} key - The configuration section key.
   * @param {Array} presets - The preset recipes for that section.
   * @returns {string|null} The active preset key, or null for a custom config.
   */
  const activePresetKey = (key, presets) => {
    const match = matchedPreset(key, presets);
    if (match) return match.key;
    return dirty ? null : configuration[key].preset_key;
  };

  /**
   * One-line description of a section, shown while it is collapsed.
   *
   * Prefers the preset the *draft* matches so an unsaved change is reflected
   * right away; falls back to the backend's resolved answer otherwise.
   *
   * @param {string} key - The configuration section key.
   * @returns {string} The summary line.
   */
  const retrieverDisplayName = (component) => {
    if (!component) return null;
    if (component === configuration.retriever_model?.component) {
      return configuration.retriever_model.display_name || component;
    }
    const found = retrieverComponents.find((item) => item.name === component);
    const displayName = found?.display_name;
    if (!displayName) return component;
    if (typeof displayName === "string") return displayName;
    return displayName[i18n.language] || displayName.en || component;
  };

  const sectionSummary = (key) => {
    const section = configuration[key];
    if (!section) return "";

    if (key === "chunking_model") {
      const preset = matchedPreset(key, chunkingPresets);
      if (preset) {
        return [preset.display_name, preset.description]
          .filter(Boolean)
          .join(", ");
      }
      return [section.preset_display_name, section.summary]
        .filter(Boolean)
        .join(", ");
    }

    if (key === "retriever_model") {
      const ref = draft.retriever_model;
      const unchanged =
        JSON.stringify(ref) === JSON.stringify(savedDraft?.retriever_model);
      const preset = matchedPreset(key, retrieverPresets);
      const presetLabel =
        preset?.display_name ||
        (unchanged ? section.preset_display_name : null);
      const retrieverLabel = retrieverDisplayName(ref?.component);
      const topK = ref?.params?.top_k ?? section.top_k;
      return [
        presetLabel,
        retrieverLabel !== presetLabel ? retrieverLabel : null,
        topK ? t("generative:rag.config.chunkCount", { count: topK }) : null,
      ]
        .filter(Boolean)
        .join(", ");
    }

    return section.display_name || "";
  };

  const sectionBody = (key) => {
    if (key === "chunking_model") {
      return (
        <Stack spacing={1.5}>
          <PresetCardList
            presets={chunkingPresets}
            activeKey={activePresetKey("chunking_model", chunkingPresets)}
            onSelect={(preset) =>
              updateSection("chunking_model", {
                component: preset.component,
                params: preset.params,
              })
            }
          />
          <Button
            variant="outlined"
            size="small"
            fullWidth
            onClick={() => setShowChunkingAdvanced(true)}
          >
            {t("generative:rag.config.advanced")}
          </Button>
          <ChunkingAdvancedModal
            open={showChunkingAdvanced}
            onClose={() => setShowChunkingAdvanced(false)}
            chunkingModel={draft.chunking_model}
            setChunkingModel={(value) => updateSection("chunking_model", value)}
          />
        </Stack>
      );
    }

    if (key === "retriever_model") {
      return (
        <Stack spacing={1.5}>
          <PresetCardList
            presets={retrieverPresets}
            activeKey={activePresetKey("retriever_model", retrieverPresets)}
            onSelect={(preset) =>
              updateSection("retriever_model", {
                component: preset.component,
                params: preset.params,
              })
            }
          />
          {retrieverDownloadMessage && (
            <Alert severity="warning" sx={{ py: 0.5 }}>
              {retrieverDownloadMessage}
            </Alert>
          )}
          <Button
            variant="outlined"
            size="small"
            fullWidth
            onClick={() => setShowRetrieverAdvanced(true)}
          >
            {t("generative:rag.config.advanced")}
          </Button>
          <RetrieverAdvancedModal
            open={showRetrieverAdvanced}
            onClose={() => setShowRetrieverAdvanced(false)}
            selectedParadigm={null}
            allParadigms={retrieverComponents}
            retrieverModel={draft.retriever_model}
            setRetrieverModel={(value) =>
              updateSection("retriever_model", value)
            }
            downloadMessage={retrieverDownloadMessage}
          />
        </Stack>
      );
    }

    if (key === "prompt") {
      return (
        <PromptEditor
          promptModel={draft.prompt}
          setPromptModel={(value) => updateSection("prompt", value)}
          onValidityChange={setPromptValid}
        />
      );
    }

    return (
      <GeneratorPicker
        generatorModel={draft.generation_model}
        setGeneratorModel={(value) => updateSection("generation_model", value)}
        onAvailabilityChange={setModelAvailable}
      />
    );
  };

  const indexNotices = [];
  if (indexStatus?.status === "indexing") {
    indexNotices.push(
      <Alert key="indexing" severity="info" sx={{ py: 0.5 }}>
        {indexStatus.message}
        <LinearProgress
          variant={
            typeof indexStatus.job?.progress === "number"
              ? "determinate"
              : "indeterminate"
          }
          value={indexStatus.job?.progress ?? 0}
          sx={{ mt: 0.75, height: 4, borderRadius: 2 }}
        />
      </Alert>,
    );
  }
  if (indexStatus?.status === "stale") {
    indexNotices.push(
      <Alert key="stale" severity="warning" sx={{ py: 0.5 }}>
        {indexStatus.message}
      </Alert>,
    );
  }
  if (
    ["error", "killed"].includes(indexStatus?.job?.status) &&
    indexStatus?.status !== "indexing"
  ) {
    indexNotices.push(
      <Alert
        key="failed"
        severity="error"
        sx={{ py: 0.5 }}
        action={
          onRetryIndexing && (
            <Button
              size="small"
              color="inherit"
              onClick={() => onRetryIndexing()}
            >
              {t("generative:rag.index.retryIndexing")}
            </Button>
          )
        }
      >
        {indexStatus.job.error || t("generative:rag.index.indexFailed")}
      </Alert>,
    );
  }
  if (
    indexStatus?.job?.status === "cancelled" &&
    ["not_indexed", "stale"].includes(indexStatus?.status)
  ) {
    indexNotices.push(
      <Alert
        key="cancelled"
        severity="warning"
        sx={{ py: 0.5 }}
        action={
          onRetryIndexing && (
            <Button
              size="small"
              color="inherit"
              onClick={() => onRetryIndexing()}
            >
              {t("generative:rag.index.retryIndexing")}
            </Button>
          )
        }
      >
        {t("generative:rag.index.indexCancelled")}
      </Alert>,
    );
  }

  return (
    <SideBar>
      <Box
        sx={{
          px: 4,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          gap: 1,
          height: 64,
        }}
      >
        <Typography
          variant="h6"
          color="text.primary"
          noWrap
          sx={{ flex: 1, minWidth: 0 }}
        >
          {name}
        </Typography>
        <Tooltip title={t("generative:rag.summary.edit")}>
          <IconButton
            size="small"
            onClick={() => setEditingMetadata((open) => !open)}
            aria-label={t("generative:rag.summary.edit")}
            color={editingMetadata ? "primary" : "default"}
          >
            <EditIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Collapse in={editingMetadata} unmountOnExit sx={{ flexShrink: 0 }}>
        <Stack
          spacing={2}
          sx={{
            p: 4,
            borderBottom: `1px solid ${theme.palette.ui.border}`,
          }}
        >
          <TextField
            size="small"
            label={t("generative:rag.summary.sessionName")}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <TextField
            size="small"
            multiline
            rows={2}
            label={t("generative:rag.summary.sessionDescription")}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button size="small" onClick={() => setEditingMetadata(false)}>
              {t("generative:rag.summary.cancel")}
            </Button>
            <Button
              size="small"
              variant="contained"
              onClick={handleSaveMetadata}
            >
              {t("generative:rag.summary.save")}
            </Button>
          </Stack>
        </Stack>
      </Collapse>

      {indexNotices.length > 0 && (
        <Stack spacing={1} sx={{ px: 4, pt: 3, flexShrink: 0 }}>
          {indexNotices}
        </Stack>
      )}

      <Box sx={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
        {SECTIONS.map((key) => {
          const section = configuration[key];
          const invalid = key === "prompt" && !promptValid;
          return (
            <Accordion
              key={key}
              expanded={expandedSection === key}
              onChange={(_event, open) => setExpandedSection(open ? key : null)}
              disableGutters
              square
              elevation={0}
              sx={{
                bgcolor: "transparent",
                borderBottom: `1px solid ${theme.palette.ui.border}`,
                "&::before": { display: "none" },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon sx={{ color: "text.secondary" }} />}
                sx={{
                  px: 4,
                  "& .MuiAccordionSummary-content": { my: 2, minWidth: 0 },
                }}
              >
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <Typography
                      variant="subtitle2"
                      color={invalid ? "error.main" : "text.primary"}
                      sx={{ fontWeight: 600 }}
                    >
                      {section.section_name}
                    </Typography>
                    {dirtySections.includes(key) && (
                      <FiberManualRecordIcon
                        sx={{ fontSize: 8 }}
                        color="warning"
                      />
                    )}
                  </Stack>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    noWrap
                    sx={{ display: "block" }}
                  >
                    {sectionSummary(key)}
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ px: 4, pt: 0, pb: 4 }}>
                {section.description && (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 3 }}
                  >
                    {section.description}
                  </Typography>
                )}
                {sectionBody(key)}
              </AccordionDetails>
            </Accordion>
          );
        })}
      </Box>

      <Box
        sx={{
          flexShrink: 0,
          px: 4,
          py: 3,
          borderTop: `1px solid ${theme.palette.ui.border}`,
          bgcolor: "background.box",
        }}
      >
        <Stack
          direction="row"
          alignItems="baseline"
          justifyContent="space-between"
          spacing={1}
        >
          <Typography variant="subtitle2">
            {t("generative:rag.config.contextBudget")}
          </Typography>
          <Typography
            variant="caption"
            color={budget.is_valid ? "text.secondary" : "error.main"}
          >
            {budgetUsed}%
          </Typography>
        </Stack>
        <LinearProgress
          variant="determinate"
          value={budgetUsed}
          color={budget.is_valid ? "primary" : "error"}
          sx={{ mt: 1, borderRadius: 1, height: 6 }}
        />
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mt: 1 }}
        >
          {t("generative:validation.contextSpace", {
            availableChars: budget.available.toLocaleString(),
          })}
        </Typography>
        {!budget.is_valid && (
          <Alert severity="error" sx={{ mt: 2, py: 0.5 }}>
            {t("generative:validation.insufficientContextDescription")}
          </Alert>
        )}

        {dirtySections.some((key) => key !== expandedSection) && (
          <Typography
            variant="caption"
            color="warning.main"
            sx={{ display: "block", mt: 2 }}
          >
            {t("generative:rag.config.unsavedIn", {
              sections: dirtySections
                .map((key) => configuration[key].section_name)
                .join(", "),
            })}
          </Typography>
        )}

        <Stack
          direction="row"
          spacing={1}
          justifyContent="flex-end"
          sx={{ mt: 3 }}
        >
          <Button onClick={handleDiscard} disabled={!dirty}>
            {t("generative:rag.config.discard")}
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={
              !dirty ||
              saving ||
              !modelAvailable ||
              !promptValid ||
              missingRetrieverDownloads.length > 0
            }
          >
            {t("generative:rag.paramsPanel.save")}
          </Button>
        </Stack>
      </Box>
    </SideBar>
  );
}

RAGConfigPanel.propTypes = {
  sessionId: PropTypes.oneOfType([PropTypes.number, PropTypes.string])
    .isRequired,
  indexStatus: PropTypes.object,
  onSaved: PropTypes.func,
  onRetryIndexing: PropTypes.func,
  onSessionRenamed: PropTypes.func,
  onGeneratorChange: PropTypes.func,
};
