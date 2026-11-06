import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import PlaylistAddIcon from "@mui/icons-material/PlaylistAdd";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { useTheme } from "@mui/material/styles";
import ModuleContainer from "../../../components/layout/ModuleContainer";
import LeftPanel from "../../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../../components/generative/SessionBar";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import DeleteConfirmationModal from "../../../components/threeSectionLayout/DeleteConfirmationModal";
import PromptLibraryCreateModal from "../../../components/generative/RAG/PromptLibraryCreateModal";
import { useGenerative } from "../../../components/generative/GenerativeContext";
import { ThreePanelLayoutContext } from "../../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { FormSchemaProvider } from "../../../contexts/schema";
import { useTaskDisplayName } from "../../../hooks/generative/useTaskDisplayName";
import { useThreePanelLayout } from "../../../hooks/useThreePanelsLayout";
import {
  RAG_TASK_NAME,
  deleteRAGPrompt,
  getLibraryPrompts,
} from "../../../api/rag";
import { getApiErrorMessage } from "../../../utils/apiError";
import { renderTemplateWithHighlights } from "../RAGSession/components/sectionUtils";

/**
 * The template of a prompt whichever shape it has.
 *
 * @param {object} prompt - A library prompt.
 * @returns {string} The template text, or an empty string.
 */
function templateOf(prompt) {
  const parameters = prompt?.parameters ?? {};
  if (typeof parameters.template === "string") return parameters.template;
  return Object.values(parameters.templates ?? {})[0] ?? "";
}

/**
 * The language a prompt declares, if any.
 *
 * @param {object} prompt - A library prompt.
 * @returns {string|null} The language code.
 */
function languageOf(prompt) {
  const parameters = prompt?.parameters ?? {};
  if (parameters.language) return parameters.language;
  return Object.keys(parameters.templates ?? {})[0] ?? null;
}

/**
 * One-line preview of a prompt template.
 *
 * @param {object} prompt - A library prompt.
 * @returns {string} The preview.
 */
function previewOf(prompt) {
  return templateOf(prompt).replace(/\s+/g, " ").slice(0, 160);
}

/**
 * The RAG prompt library: prompts the user saved, with create and delete.
 *
 * @returns {JSX.Element} The prompt library page.
 */
export default function RAGPromptsPage() {
  const navigate = useNavigate();
  const { t } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const threePanelLayout = useThreePanelLayout({ storageKey: "rag-prompts" });
  const { sessions, deleteSessionById, fetchSessions } = useGenerative();
  const ragTitle = useTaskDisplayName(RAG_TASK_NAME);

  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createTemplate, setCreateTemplate] = useState("");
  const [createType, setCreateType] = useState("");
  const [createSubtype, setCreateSubtype] = useState("");
  const [pendingDelete, setPendingDelete] = useState(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [subtypeFilter, setSubtypeFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setLoadFailed(false);
    try {
      setPrompts(await getLibraryPrompts());
    } catch (error) {
      console.error("Failed to load prompt library:", error);
      setLoadFailed(true);
      enqueueSnackbar(t("generative:rag.prompt.library.loadError"), {
        variant: "error",
      });
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar, t]);

  useEffect(() => {
    load();
  }, [load]);

  const selected = useMemo(
    () => prompts.find((prompt) => prompt.id === selectedId) ?? null,
    [prompts, selectedId],
  );

  const typeOptions = useMemo(
    () => [
      ...new Set(prompts.map((prompt) => prompt.prompt_type).filter(Boolean)),
    ],
    [prompts],
  );

  const subtypeOptions = useMemo(
    () => [
      ...new Set(
        prompts
          .filter((prompt) => !typeFilter || prompt.prompt_type === typeFilter)
          .map((prompt) => prompt.prompt_subtype)
          .filter(Boolean),
      ),
    ],
    [prompts, typeFilter],
  );

  const filteredPrompts = useMemo(
    () =>
      prompts.filter(
        (prompt) =>
          (!typeFilter || prompt.prompt_type === typeFilter) &&
          (!subtypeFilter || prompt.prompt_subtype === subtypeFilter),
      ),
    [prompts, typeFilter, subtypeFilter],
  );

  const handleTypeFilterChange = (value) => {
    setTypeFilter(value);
    setSubtypeFilter("");
  };

  const handleCreated = useCallback(
    async (promptId) => {
      await load();
      setTypeFilter("");
      setSubtypeFilter("");
      setSelectedId(promptId);
    },
    [load],
  );

  const handleNewPrompt = () => {
    setCreateTemplate("");
    setCreateType("");
    setCreateSubtype("");
    setCreateOpen(true);
  };

  const handleUseAsBase = () => {
    if (!selected) return;
    setCreateTemplate(templateOf(selected));
    setCreateType(selected.prompt_type ?? "");
    setCreateSubtype(selected.prompt_subtype ?? "");
    setCreateOpen(true);
  };

  const handleCopyTemplate = async () => {
    const template = templateOf(selected);
    if (!template) return;
    try {
      await navigator.clipboard.writeText(template);
      enqueueSnackbar(t("generative:rag.prompt.library.copied"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Failed to copy prompt template:", error);
      enqueueSnackbar(t("generative:rag.prompt.library.copyError"), {
        variant: "error",
      });
    }
  };

  const handleDelete = async () => {
    const prompt = pendingDelete;
    if (!prompt) return;
    try {
      // Ask the server first. If it reports sessions the dialog did not
      // name, keep it open with the fresh list instead of silently deleting
      // them based on a stale page.
      await deleteRAGPrompt(prompt.id, Boolean(prompt.cascadeConfirmed));
      setPendingDelete(null);
      setPrompts((previous) =>
        previous.filter((item) => item.id !== prompt.id),
      );
      if (selectedId === prompt.id) setSelectedId(null);
      fetchSessions?.();
      enqueueSnackbar(t("generative:rag.prompt.library.deleted"), {
        variant: "success",
      });
    } catch (error) {
      const sessionsUsing = error.response?.data?.detail?.sessions;
      if (
        !prompt.cascadeConfirmed &&
        error.response?.status === 409 &&
        Array.isArray(sessionsUsing)
      ) {
        const shownIds = new Set(
          (prompt.sessions ?? []).map((session) => session.id),
        );
        if (sessionsUsing.every((session) => shownIds.has(session.id))) {
          // The user already saw exactly these sessions: cascade now.
          try {
            await deleteRAGPrompt(prompt.id, true);
            setPendingDelete(null);
            setPrompts((previous) =>
              previous.filter((item) => item.id !== prompt.id),
            );
            if (selectedId === prompt.id) setSelectedId(null);
            fetchSessions?.();
            enqueueSnackbar(t("generative:rag.prompt.library.deleted"), {
              variant: "success",
            });
            return;
          } catch (cascadeError) {
            error = cascadeError;
          }
        } else {
          setPendingDelete({
            ...prompt,
            sessions: sessionsUsing,
            cascadeConfirmed: true,
          });
          return;
        }
      }
      console.error("Failed to delete prompt:", error);
      enqueueSnackbar(
        getApiErrorMessage(
          error,
          t("generative:rag.prompt.library.deleteError"),
        ),
        { variant: "error" },
      );
    }
  };

  const deleteWarning =
    pendingDelete?.sessions?.length > 0
      ? t("generative:rag.prompt.library.deleteCascadeWarning", {
          sessions: pendingDelete.sessions
            .map((session) => session.name)
            .join(", "),
        })
      : t("generative:rag.prompt.library.deleteWarning");

  const placeholderColors = useMemo(
    () => ({
      bg: theme.palette.secondary.light,
      text: theme.palette.secondary.dark,
    }),
    [theme],
  );

  return (
    <FormSchemaProvider>
      <ThreePanelLayoutContext.Provider value={threePanelLayout}>
        <ModuleContainer>
          <LeftPanel data-tour="sessions-left-panel">
            <SessionBar
              sessions={sessions}
              handleSessionClick={(sessionId) =>
                navigate(`/app/generative/rag/sessions/${sessionId}`)
              }
              handleNewSessionButton={() => navigate("/app/generative/rag")}
              handleSessionDelete={deleteSessionById}
              onToggle={threePanelLayout.handleToggleLeft}
              showSearch={false}
              title={ragTitle}
            />
          </LeftPanel>

          <CenterPanel data-tour="prompts-center-panel">
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                height: "100%",
                minHeight: 0,
                p: 4,
              }}
            >
              <RAGBreadcrumbs />
              <Stack spacing={2} sx={{ mb: 3 }}>
                <Stack
                  direction="row"
                  alignItems="flex-start"
                  justifyContent="space-between"
                  spacing={2}
                  useFlexGap
                  sx={{ flexWrap: "wrap" }}
                >
                  <Box sx={{ flex: "1 1 260px", minWidth: 0 }}>
                    <Typography variant="h5" component="h2">
                      {t("generative:rag.prompt.library.title")}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t("generative:rag.prompt.library.subtitle")}
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={handleNewPrompt}
                  >
                    {t("generative:rag.prompt.library.new")}
                  </Button>
                </Stack>

                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  useFlexGap
                  sx={{ flexWrap: "wrap" }}
                >
                  <TextField
                    select
                    size="small"
                    label={t("generative:rag.prompt.library.filterType")}
                    value={typeFilter}
                    onChange={(event) =>
                      handleTypeFilterChange(event.target.value)
                    }
                    sx={{ minWidth: 160 }}
                  >
                    <MenuItem value="">
                      {t("generative:rag.prompt.library.allTypes")}
                    </MenuItem>
                    {typeOptions.map((type) => (
                      <MenuItem key={type} value={type}>
                        {t(`generative:rag.prompt.library.types.${type}`, {
                          defaultValue: type,
                        })}
                      </MenuItem>
                    ))}
                  </TextField>
                  {subtypeOptions.length > 0 && (
                    <TextField
                      select
                      size="small"
                      label={t("generative:rag.prompt.library.filterSubtype")}
                      value={subtypeFilter}
                      onChange={(event) => setSubtypeFilter(event.target.value)}
                      sx={{ minWidth: 160 }}
                    >
                      <MenuItem value="">
                        {t("generative:rag.prompt.library.allSubtypes")}
                      </MenuItem>
                      {subtypeOptions.map((subtype) => (
                        <MenuItem key={subtype} value={subtype}>
                          {t(
                            `generative:rag.prompt.library.subtypes.${subtype}`,
                            { defaultValue: subtype },
                          )}
                        </MenuItem>
                      ))}
                    </TextField>
                  )}
                </Stack>
              </Stack>

              <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", pr: 1 }}>
                {loading ? (
                  <Box
                    sx={{ display: "flex", justifyContent: "center", py: 6 }}
                  >
                    <CircularProgress />
                  </Box>
                ) : loadFailed ? (
                  <Typography color="text.secondary">
                    {t("generative:rag.prompt.library.loadError")}
                  </Typography>
                ) : prompts.length === 0 ? (
                  <Box sx={{ textAlign: "center", py: 8 }}>
                    <Typography color="text.secondary" sx={{ mb: 2 }}>
                      {t("generative:rag.prompt.library.empty")}
                    </Typography>
                    <Button
                      variant="outlined"
                      startIcon={<AddIcon />}
                      onClick={handleNewPrompt}
                    >
                      {t("generative:rag.prompt.library.new")}
                    </Button>
                  </Box>
                ) : filteredPrompts.length === 0 ? (
                  <Typography
                    color="text.secondary"
                    sx={{ textAlign: "center", py: 8 }}
                  >
                    {t("generative:rag.prompt.library.noMatches")}
                  </Typography>
                ) : (
                  <Stack spacing={1.5}>
                    {filteredPrompts.map((prompt) => {
                      const language = languageOf(prompt);
                      return (
                        <Paper
                          key={prompt.id}
                          variant="outlined"
                          onClick={() => setSelectedId(prompt.id)}
                          sx={{
                            p: 2,
                            cursor: "pointer",
                            bgcolor:
                              selectedId === prompt.id
                                ? "action.selected"
                                : "background.paper",
                            borderColor:
                              selectedId === prompt.id
                                ? "secondary.main"
                                : "divider",
                            transition:
                              "border-color 150ms ease-out, background-color 150ms ease-out",
                            "@media (hover: hover)": {
                              "&:hover": {
                                borderColor: "secondary.main",
                              },
                            },
                          }}
                        >
                          <Stack
                            direction="row"
                            spacing={2}
                            alignItems="center"
                          >
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              <Typography variant="subtitle1" noWrap>
                                {prompt.name || `Prompt ${prompt.id}`}
                              </Typography>
                              <Typography
                                variant="body2"
                                color="text.secondary"
                                noWrap
                                sx={{ mt: 0.5 }}
                              >
                                {previewOf(prompt)}
                              </Typography>
                              <Stack
                                direction="row"
                                spacing={1}
                                sx={{ mt: 1, flexWrap: "wrap" }}
                              >
                                {prompt.prompt_type && (
                                  <Chip
                                    size="small"
                                    color="info"
                                    variant="outlined"
                                    label={t(
                                      `generative:rag.prompt.library.types.${prompt.prompt_type}`,
                                      { defaultValue: prompt.prompt_type },
                                    )}
                                  />
                                )}
                                {language && (
                                  <Chip
                                    size="small"
                                    variant="outlined"
                                    label={
                                      t(
                                        `generative:rag.prompt.languages.${language}`,
                                      ) || language
                                    }
                                  />
                                )}
                                {!prompt.is_library && (
                                  <Chip
                                    size="small"
                                    variant="outlined"
                                    label={t(
                                      "generative:rag.prompt.library.builtin",
                                    )}
                                  />
                                )}
                                <Chip
                                  size="small"
                                  color={
                                    (prompt.sessions ?? []).length > 0
                                      ? "secondary"
                                      : "default"
                                  }
                                  label={t(
                                    "generative:rag.prompt.library.sessionCount",
                                    { count: (prompt.sessions ?? []).length },
                                  )}
                                />
                              </Stack>
                            </Box>
                            <Tooltip
                              title={t("generative:rag.prompt.library.view")}
                            >
                              <IconButton
                                aria-label={t(
                                  "generative:rag.prompt.library.view",
                                )}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setSelectedId(prompt.id);
                                }}
                              >
                                <VisibilityIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            {prompt.is_library && (
                              <Tooltip
                                title={t(
                                  "generative:rag.prompt.library.delete",
                                )}
                              >
                                <IconButton
                                  aria-label={t(
                                    "generative:rag.prompt.library.delete",
                                  )}
                                  color="error"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    setPendingDelete(prompt);
                                  }}
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Stack>
                        </Paper>
                      );
                    })}
                  </Stack>
                )}
              </Box>
            </Box>
          </CenterPanel>

          <RightPanel toggleButtonTop="50%">
            <Box
              sx={{
                height: "100%",
                overflowY: "auto",
                bgcolor: "background.box",
                p: 2,
              }}
            >
              {selected ? (
                <Stack spacing={2}>
                  <Box>
                    <Typography variant="h6">
                      {selected.name || `Prompt ${selected.id}`}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {selected.class_name}
                    </Typography>
                    <Stack direction="row" spacing={0.5} sx={{ mt: 1 }}>
                      <Tooltip
                        title={t("generative:rag.prompt.library.copyTemplate")}
                      >
                        <IconButton
                          size="small"
                          aria-label={t(
                            "generative:rag.prompt.library.copyTemplate",
                          )}
                          onClick={handleCopyTemplate}
                        >
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip
                        title={t("generative:rag.prompt.library.useAsBase")}
                      >
                        <IconButton
                          size="small"
                          aria-label={t(
                            "generative:rag.prompt.library.useAsBase",
                          )}
                          onClick={handleUseAsBase}
                        >
                          <PlaylistAddIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </Box>
                  <Divider />
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      {t("generative:rag.prompt.library.template")}
                    </Typography>
                    <Box
                      sx={{
                        p: 2,
                        border: 1,
                        borderColor: "divider",
                        borderRadius: 1,
                        bgcolor: "background.paper",
                        fontFamily: theme.typography.code.fontFamily,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        lineHeight: 1.6,
                      }}
                    >
                      {renderTemplateWithHighlights(
                        templateOf(selected),
                        placeholderColors,
                        theme.typography.code.fontFamily,
                      ) ?? (
                        <Typography variant="body2" color="text.secondary">
                          {t("generative:rag.prompt.library.noTemplate")}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      {t("generative:rag.prompt.library.usedBy")}
                    </Typography>
                    {(selected.sessions ?? []).length === 0 ? (
                      <Typography variant="body2" color="text.secondary">
                        {t("generative:rag.prompt.library.notUsed")}
                      </Typography>
                    ) : (
                      <Stack spacing={0.5}>
                        {(selected.sessions ?? []).map((session) => (
                          <Typography key={session.id} variant="body2">
                            {session.name}
                          </Typography>
                        ))}
                      </Stack>
                    )}
                  </Box>
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {t("generative:rag.prompt.library.selectPrompt")}
                </Typography>
              )}
            </Box>
          </RightPanel>
        </ModuleContainer>

        <PromptLibraryCreateModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreated={handleCreated}
          initialTemplate={createTemplate}
          initialType={createType}
          initialSubtype={createSubtype}
        />

        <DeleteConfirmationModal
          open={pendingDelete !== null}
          onClose={() => setPendingDelete(null)}
          onConfirm={handleDelete}
          content={t("generative:rag.prompt.library.deleteConfirm", {
            name: pendingDelete?.name ?? "",
          })}
          warning={deleteWarning}
        />
      </ThreePanelLayoutContext.Provider>
    </FormSchemaProvider>
  );
}
