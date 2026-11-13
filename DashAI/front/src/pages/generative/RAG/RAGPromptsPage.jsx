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
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import FileCopyIcon from "@mui/icons-material/FileCopy";
import PlaylistAddIcon from "@mui/icons-material/PlaylistAdd";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { useTheme } from "@mui/material/styles";
import {
  MaterialReactTable,
  useMaterialReactTable,
} from "material-react-table";
import ModuleContainer from "../../../components/layout/ModuleContainer";
import LeftPanel from "../../../components/threeSectionLayout/panels/LeftPanel";
import CenterPanel from "../../../components/threeSectionLayout/panels/CenterPanel";
import RightPanel from "../../../components/threeSectionLayout/panels/RightPanel";
import SessionBar from "../../../components/generative/SessionBar";
import RAGBreadcrumbs from "../../../components/generative/RAG/RAGBreadcrumbs";
import DeleteConfirmationModal from "../../../components/threeSectionLayout/DeleteConfirmationModal";
import PromptLibraryCreateModal from "../../../components/generative/RAG/PromptLibraryCreateModal";
import PromptLibraryEditModal from "../../../components/generative/RAG/PromptLibraryEditModal";
import { useGenerative } from "../../../components/generative/GenerativeContext";
import { ThreePanelLayoutContext } from "../../../components/threeSectionLayout/panels/ThreePanelLayoutContext";
import { FormSchemaProvider } from "../../../contexts/schema";
import { useTaskDisplayName } from "../../../hooks/generative/useTaskDisplayName";
import { useThreePanelLayout } from "../../../hooks/useThreePanelsLayout";
import {
  RAG_TASK_NAME,
  deleteRAGPrompt,
  forkRAGPrompt,
  getLibraryPrompts,
} from "../../../api/rag";
import { getApiErrorMessage } from "../../../utils/apiError";
import { useTableLocalization } from "../../../utils/useTableLocalization";
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
 * The RAG prompt library: prompts the user saved, with create and delete.
 *
 * @returns {JSX.Element} The prompt library page.
 */
export default function RAGPromptsPage() {
  const navigate = useNavigate();
  const { t } = useTranslation(["generative", "common"]);
  const { enqueueSnackbar } = useSnackbar();
  const theme = useTheme();
  const localization = useTableLocalization();
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
  const [editOpen, setEditOpen] = useState(false);
  const [editPromptId, setEditPromptId] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
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

  const handleEdit = useCallback((prompt) => {
    setEditPromptId(prompt.id);
    setEditOpen(true);
  }, []);

  const handleDuplicate = useCallback(
    async (prompt) => {
      // Only a built-in can be duplicated: forking it creates a `Custom*` library
      // row. Forking a library row returns its own content (the API keys rows by
      // content hash), so the action would either fail with a 409 or report a
      // copy that was never created. Library rows use "Use as base" instead.
      if (!prompt?.is_default) return;
      const sourceName = prompt.name || `Prompt ${prompt.id}`;
      // Ids already on screen tell us whether the fork created a row or the API
      // handed back an existing one; the two must not be reported the same way.
      const knownIds = new Set(prompts.map((item) => item.id));
      try {
        const created = await forkRAGPrompt(prompt.id, {
          name: `${sourceName}${t("generative:rag.prompt.library.copySuffix")}`,
        });
        await load();
        setTypeFilter("");
        setSubtypeFilter("");
        setSelectedId(created.id);
        setEditPromptId(created.id);
        setEditOpen(true);
        fetchSessions?.();
        const createdNow = !knownIds.has(created.id);
        enqueueSnackbar(
          createdNow
            ? t("generative:rag.prompt.library.duplicated")
            : t("generative:rag.prompt.library.duplicateExisting", {
                name: created.name || sourceName,
              }),
          { variant: createdNow ? "success" : "info" },
        );
      } catch (error) {
        console.error("Failed to duplicate prompt:", error);
        enqueueSnackbar(
          getApiErrorMessage(
            error,
            t("generative:rag.prompt.library.createError"),
          ),
          { variant: "error" },
        );
      }
    },
    [prompts, load, t, enqueueSnackbar, fetchSessions],
  );

  const handleEditSaved = useCallback(
    async (promptId) => {
      await load();
      setSelectedId(promptId);
      fetchSessions?.();
    },
    [load, fetchSessions],
  );

  /**
   * Delete the pending prompt.
   *
   * `mode` mirrors the API's two ways out of an in-use prompt: "detach" keeps
   * the sessions and repoints them, "cascade" deletes them. Without a mode the
   * prompt is deleted only when nothing uses it; a 409 then reopens the dialog
   * with the server's authoritative session list so the user can pick.
   *
   * @param {"detach"|"cascade"} [mode] - How to handle sessions using it.
   */
  const handleDelete = async (mode) => {
    const prompt = pendingDelete;
    if (!prompt) return;
    setDeleting(true);
    try {
      await deleteRAGPrompt(prompt.id, mode === "cascade", mode === "detach");
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
        error.response?.status === 409 &&
        Array.isArray(sessionsUsing) &&
        sessionsUsing.length > 0
      ) {
        // The server is the source of truth for who uses this prompt: show
        // exactly those sessions instead of acting on a stale page.
        setPendingDelete({ ...prompt, sessions: sessionsUsing });
        return;
      }
      console.error("Failed to delete prompt:", error);
      enqueueSnackbar(
        getApiErrorMessage(
          error,
          t("generative:rag.prompt.library.deleteError"),
        ),
        { variant: "error" },
      );
    } finally {
      setDeleting(false);
    }
  };

  const pendingDeleteSessions = pendingDelete?.sessions ?? [];
  const hasSessions = pendingDeleteSessions.length > 0;

  const deleteWarning = hasSessions
    ? t("generative:rag.prompt.library.deleteOptionsHelp", {
        sessions: pendingDeleteSessions
          .map((session) => session.name)
          .join(", "),
      })
    : t("generative:rag.prompt.library.deleteWarning");

  const placeholderColors = useMemo(
    () => ({
      bg: theme.palette.placeholder.bg,
      text: theme.palette.placeholder.text,
    }),
    [theme],
  );

  const columns = useMemo(
    () => [
      {
        accessorKey: "name",
        header: t("common:name"),
        minSize: 150,
        accessorFn: (prompt) => prompt.name || `Prompt ${prompt.id}`,
      },
      {
        accessorKey: "prompt_type",
        header: t("generative:rag.prompt.library.filterType"),
        minSize: 110,
        accessorFn: (prompt) => {
          if (!prompt.prompt_type) return "";
          const type = t(
            `generative:rag.prompt.library.types.${prompt.prompt_type}`,
            { defaultValue: prompt.prompt_type },
          );
          if (!prompt.prompt_subtype) return type;
          const subtype = t(
            `generative:rag.prompt.library.subtypes.${prompt.prompt_subtype}`,
            { defaultValue: prompt.prompt_subtype },
          );
          return `${type} · ${subtype}`;
        },
      },
      {
        id: "origin",
        header: t("generative:rag.prompt.library.origin"),
        enableSorting: false,
        minSize: 90,
        Cell: ({ row }) => {
          if (row.original.is_default) {
            return (
              <Chip
                size="small"
                variant="outlined"
                label={t("generative:rag.prompt.library.builtin")}
              />
            );
          }
          if (row.original.is_library) {
            return (
              <Chip
                size="small"
                variant="outlined"
                label={t("generative:rag.prompt.library.library")}
              />
            );
          }
          return null;
        },
      },
      {
        id: "sessions",
        header: t("generative:rag.prompt.library.sessions"),
        accessorFn: (prompt) => (prompt.sessions ?? []).length,
        minSize: 70,
        Cell: ({ row }) => {
          const count = (row.original.sessions ?? []).length;
          return (
            <Chip
              size="small"
              color={count > 0 ? "secondary" : "default"}
              label={String(count)}
              aria-label={t("generative:rag.prompt.library.sessionCount", {
                count,
              })}
            />
          );
        },
      },
      {
        id: "actions",
        header: t("common:actions"),
        enableSorting: false,
        minSize: 140,
        Cell: ({ row }) => {
          const prompt = row.original;
          const displayName = prompt.name || `Prompt ${prompt.id}`;
          return (
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Tooltip title={t("generative:rag.prompt.library.view")}>
                <IconButton
                  size="small"
                  aria-label={`${t(
                    "generative:rag.prompt.library.view",
                  )}: ${displayName}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    setSelectedId(prompt.id);
                  }}
                >
                  <VisibilityIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              {prompt.is_library && !prompt.is_default && (
                <Tooltip title={t("generative:rag.prompt.library.edit")}>
                  <IconButton
                    size="small"
                    aria-label={`${t(
                      "generative:rag.prompt.library.edit",
                    )}: ${displayName}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      handleEdit(prompt);
                    }}
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              {prompt.is_default && (
                <Tooltip title={t("generative:rag.prompt.library.duplicate")}>
                  <IconButton
                    size="small"
                    aria-label={`${t(
                      "generative:rag.prompt.library.duplicate",
                    )}: ${displayName}`}
                    onClick={(event) => {
                      event.stopPropagation();
                      handleDuplicate(prompt);
                    }}
                  >
                    <FileCopyIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              {prompt.is_library && (
                <Tooltip title={t("generative:rag.prompt.library.delete")}>
                  <IconButton
                    size="small"
                    color="error"
                    aria-label={`${t(
                      "generative:rag.prompt.library.delete",
                    )}: ${displayName}`}
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
          );
        },
      },
    ],
    [t, handleEdit, handleDuplicate],
  );

  const table = useMaterialReactTable({
    columns,
    data: filteredPrompts,
    getRowId: (prompt) => String(prompt.id),
    localization,
    mrtTheme: { baseBackgroundColor: theme.palette.ui.panelDark },
    layoutMode: "grid",
    muiTableBodyCellProps: {
      sx: { whiteSpace: "pre", overflow: "hidden", textOverflow: "ellipsis" },
    },
    muiTableHeadCellProps: { sx: { whiteSpace: "nowrap" } },
    defaultColumn: { minSize: 60, maxSize: 260 },
    muiTableProps: { sx: { tableLayout: "fixed", width: "100%" } },
    muiTablePaperProps: {
      elevation: 0,
      sx: {
        height: "100%",
        width: "100%",
        maxWidth: "100%",
        display: "flex",
        flexDirection: "column",
      },
    },
    muiTableContainerProps: {
      sx: { flex: 1, minHeight: 0, overflowX: "auto", overflowY: "auto" },
    },
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => setSelectedId(row.original.id),
      sx: {
        cursor: "pointer",
        backgroundColor:
          selectedId === row.original.id ? "action.selected" : undefined,
        "&:hover": {
          backgroundColor:
            selectedId === row.original.id ? "action.selected" : "action.hover",
        },
      },
    }),
    initialState: {
      density: "compact",
      pagination: { pageSize: 5, pageIndex: 0 },
    },
    enablePagination: true,
    enableBottomToolbar: true,
    enableTopToolbar: false,
    enableColumnFilters: false,
    enableColumnActions: false,
    enableColumnResizing: false,
    enableGlobalFilter: false,
    enableRowSelection: false,
    enableDensityToggle: false,
    enableFullScreenToggle: false,
    enableHiding: false,
    pageSizeOptions: [5, 10, 25],
    renderEmptyRowsFallback: () => (
      <Box sx={{ px: 2, py: 6, textAlign: "center" }}>
        <Typography
          color="text.secondary"
          sx={{ mb: prompts.length === 0 ? 2 : 0 }}
        >
          {prompts.length === 0
            ? t("generative:rag.prompt.library.empty")
            : t("generative:rag.prompt.library.noMatches")}
        </Typography>
        {prompts.length === 0 && (
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleNewPrompt}
          >
            {t("generative:rag.prompt.library.new")}
          </Button>
        )}
      </Box>
    ),
  });

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

              <Box
                sx={{
                  flex: 1,
                  minHeight: 0,
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                {loading ? (
                  <Box
                    sx={{ display: "flex", justifyContent: "center", py: 6 }}
                  >
                    <CircularProgress />
                  </Box>
                ) : loadFailed ? (
                  <Stack
                    spacing={2}
                    alignItems="center"
                    sx={{ textAlign: "center", py: 6 }}
                  >
                    <Typography color="text.secondary">
                      {t("generative:rag.prompt.library.loadError")}
                    </Typography>
                    <Button variant="outlined" onClick={load}>
                      {t("generative:rag.prompt.library.retry")}
                    </Button>
                  </Stack>
                ) : (
                  <MaterialReactTable table={table} />
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

        <PromptLibraryEditModal
          open={editOpen}
          onClose={() => setEditOpen(false)}
          promptId={editPromptId}
          onSaved={handleEditSaved}
        />

        <DeleteConfirmationModal
          open={pendingDelete !== null}
          onClose={() => setPendingDelete(null)}
          onConfirm={() => handleDelete(hasSessions ? "cascade" : undefined)}
          confirmLabel={
            hasSessions
              ? t("generative:rag.prompt.library.deleteCascadeSessions")
              : undefined
          }
          // Deleting the sessions is the irreversible choice, so it is never
          // the emphasised one: "Keep sessions" is the safe default.
          confirmVariant={hasSessions ? "outlined" : "text"}
          onSecondary={hasSessions ? () => handleDelete("detach") : undefined}
          secondaryLabel={
            hasSessions
              ? t("generative:rag.prompt.library.deleteKeepSessions")
              : undefined
          }
          secondaryVariant={hasSessions ? "contained" : "outlined"}
          deleting={deleting}
          content={t("generative:rag.prompt.library.deleteConfirm", {
            name: pendingDelete?.name ?? "",
          })}
          warning={deleteWarning}
          warningSeverity={hasSessions ? "warning" : "error"}
        />
      </ThreePanelLayoutContext.Provider>
    </FormSchemaProvider>
  );
}
