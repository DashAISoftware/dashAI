import { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Box, CircularProgress, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import {
  getModelSessionById,
  getPreprocessedColumns,
  updateSessionConverters,
} from "../../api/modelSession";
import {
  getCurrentDataFilePath,
  pollSessionPreprocessing,
} from "../../utils/sessionPreprocessing";
import { startJobPolling } from "../../utils/jobPoller";
import { useModels } from "./ModelsContext";
import { useExplorersAndConverters } from "../notebooks/context/ExplorersAndConvertersContext";
import AppliedConvertersView from "./modelSession/AppliedConvertersView";
import SessionConvertersRightBar from "./modelSession/SessionConvertersRightBar";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";

// preprocessing_status values (see the backend's SessionPreprocessingStatus
// enum): 0=NOT_STARTED, 1=DELIVERED, 2=STARTED, 3=FINISHED, 4=ERROR.
const DELIVERED = 1;
const STARTED = 2;

/**
 * Second wizard step (of three): live preprocessing preview. The session
 * record already exists by the time this step is reachable (created at the
 * end of step 0, in CreateSessionSteps.jsx) — this step's job is only to
 * let the user apply/remove converters against it and preview the result,
 * via the real `/model-session/{id}/converters` endpoint. Converters are
 * configured from the sidebar pushed into `sessionRightContent`
 * (SessionConvertersRightBar); the center panel renders the session's
 * current data plus a card per already-applied converter
 * (AppliedConvertersView). The session itself, not `newExp`, is the source
 * of truth here — `newExp.converters` was only ever meaningful back when
 * converters were client-side-only, before step 1 existed.
 */
function PreprocessingStep({
  newExp,
  dataset,
  modelSessionId,
  refreshTrigger,
  isActive = true,
  onBack,
  onCreateSession,
}) {
  const { setSessionRightContent } = useModels();
  const { t } = useTranslation(["models", "datasets", "common"]);
  const theme = useTheme();
  const { setPendingDropTool } = useExplorersAndConverters();
  const [columnTypes, setColumnTypes] = useState({});
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const [session, setSession] = useState(null);
  const [isApplying, setIsApplying] = useState(false);

  // Mirrors the notebook's NotebookView.jsx drop target: same window-level
  // dragstart/dragend listeners driving the same "is a converter card being
  // dragged right now" overlay, so dropping one here behaves exactly like
  // dropping it onto the sidebar's own cards.
  useEffect(() => {
    const onStart = (e) => {
      if (e.dataTransfer.types.includes("application/x-dashai-tool")) {
        setIsDragging(true);
      }
    };
    const onEnd = () => {
      setIsDragging(false);
      setIsDragOver(false);
    };
    window.addEventListener("dragstart", onStart);
    window.addEventListener("dragend", onEnd);
    return () => {
      window.removeEventListener("dragstart", onStart);
      window.removeEventListener("dragend", onEnd);
    };
  }, []);

  const handleDragOver = (e) => {
    if (!e.dataTransfer.types.includes("application/x-dashai-tool")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
  };

  const handleDragEnter = (e) => {
    if (!e.dataTransfer.types.includes("application/x-dashai-tool")) return;
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    const related = e.relatedTarget;
    if (!related || !e.currentTarget.contains(related)) {
      setIsDragOver(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    try {
      const tool = JSON.parse(
        e.dataTransfer.getData("application/x-dashai-tool"),
      );
      if (tool?.name) setPendingDropTool(tool);
    } catch {
      // ignore invalid drops
    }
  };

  // Stable across renders (deps only on modelSessionId) — this is passed to
  // SessionConvertersRightBar as `onConvertersChanged`, which in turn feeds
  // its own `SessionFormSection` useMemo alongside `session` itself. That
  // memo's whole purpose is keeping the ConfigureToolModal form mounted
  // while the user is mid-configuration, so `session` must only change at
  // well-defined boundaries (mount, an explicit remove, or a converter
  // apply finishing/erroring) — never from a background/continuous poll —
  // or an open modal would remount and silently lose the user's in-progress
  // scope/parameter selection.
  // GET /model-session/{id} never returns a nested `dataset` object (only
  // `dataset_id`) — `getCurrentDataFilePath` needs the real dataset's
  // `file_path` whenever `preprocessed_path` isn't set yet (i.e. before any
  // converter has been applied), so every `session` this component hands
  // downstream is patched with the `dataset` prop it already has from step 0.
  const setSessionWithDataset = useCallback(
    (nextSession) =>
      setSession(
        nextSession
          ? { ...nextSession, dataset: nextSession.dataset || dataset }
          : nextSession,
      ),
    [dataset],
  );

  const refreshSession = useCallback(async () => {
    try {
      const fresh = await getModelSessionById(modelSessionId);
      setSessionWithDataset(fresh);
      setIsApplying(
        fresh.preprocessing_status === DELIVERED ||
          fresh.preprocessing_status === STARTED,
      );
      // The scope picker every converter is configured against must offer the
      // session's *current* columns, not the raw dataset's — that's the whole
      // point of applying converters for real here. A second converter scoped
      // to a column a first one already renamed away (PCA, feature selectors,
      // text vectorizers) sends the backend a scope it can't resolve.
      // `GET /preprocessed-columns` returns the same
      // `{name: {type, dtype}}` shape `GET /dataset/{id}/types` did (and
      // transparently falls back to the raw dataset while no converter has
      // been applied yet), so it drops straight into the same state. Fetched
      // here rather than in its own effect so it re-reads on exactly the same
      // occasions the session does: mount, every apply, every removal, and
      // every return from step 0.
      try {
        const { columns } = await getPreprocessedColumns(modelSessionId);
        setColumnTypes(columns || {});
      } catch (error) {
        console.error("Error fetching session columns:", error);
      }
      return fresh;
    } catch (error) {
      console.error("Error fetching model session:", error);
      return null;
    }
  }, [modelSessionId, setSessionWithDataset]);

  useEffect(() => {
    refreshSession();
    // refreshTrigger isn't read inside refreshSession — it's a pure
    // re-run signal, bumped by CreateSessionSteps every time step 0
    // advances back into this step, so a split change that invalidated
    // converters (see that component's `converters_invalidated` handling)
    // is picked up even though this component never unmounts.
  }, [refreshSession, refreshTrigger]);

  // Called synchronously by FormSessionConverterSection (via
  // SessionConvertersRightBar) the instant a converter save begins — before
  // its PUT request fires. This is what actually closes the add-side race:
  // isApplying flips true here immediately, which disables every converter
  // card in the sidebar (see SessionConvertersRightBar's `disabled:
  // isApplying`), so a second "add" can never be started — and therefore
  // can never build its PUT payload from a stale, pre-first-converter
  // `session.converters` — while the first one is still in flight. Stable
  // identity (no deps) since it only ever calls setIsApplying.
  const handleApplyStart = useCallback(() => {
    setIsApplying(true);
  }, []);

  // Removal is initiated here (unlike adding, which lives entirely inside
  // FormSessionConverterSection via the sidebar), so this is the one place
  // that can optimistically flip isApplying the moment the request starts,
  // rather than only learning about it after the fact.
  const handleRemoveConverter = async (index) => {
    if (!session) return;
    setIsApplying(true);
    // Cascade delete, matching the notebook's own converter removal
    // (NotebookView.jsx's getItemsToDelete/handleConfirmConverterDelete):
    // removing a converter also removes every converter applied after it,
    // since a later converter may have been scoped against columns this
    // one produced — keeping it would silently re-fit it against a scope
    // that no longer exists. AppliedConvertersView already confirms this
    // with the user (via ItemsToDeleteList) before calling this handler.
    const nextConverters = (session.converters || []).slice(0, index);
    try {
      const updated = await updateSessionConverters(
        modelSessionId,
        nextConverters,
      );
      setSessionWithDataset(updated);
      // A cleared converter list resolves synchronously on the backend (no
      // job is enqueued for an empty list — see the /converters endpoint),
      // so there is nothing to poll for in that case.
      if (nextConverters.length === 0) {
        setIsApplying(false);
        return;
      }
      // Wakes the shared job-queue widget the same way the add path does
      // (see FormSessionConverterSection) — pure visibility signal, the
      // actual state transition below still comes from
      // pollSessionPreprocessing.
      if (updated?.preprocessing_huey_id) {
        startJobPolling(
          updated.preprocessing_huey_id,
          () => {},
          () => {},
        );
      }
      pollSessionPreprocessing(modelSessionId, {
        onFinished: (finalSession) => {
          setSessionWithDataset(finalSession);
          setIsApplying(false);
        },
        onError: (finalSession) => {
          // pollSessionPreprocessing calls this with two different shapes:
          // a terminal preprocessing error passes the session, a
          // network/request failure mid-poll passes (null, error) — never
          // assume the first argument is a real session object.
          if (finalSession) setSessionWithDataset(finalSession);
          setIsApplying(false);
        },
      });
      // The returned cancel fn only matters if this component unmounts
      // mid-poll; a full unmount during a remove is an acceptable edge
      // case here, same as it already is for FormSessionConverterSection's
      // own poll.
    } catch (error) {
      console.error("Error removing converter:", error);
      setIsApplying(false);
    }
  };

  // Push the converters sidebar into the shared right-bar slot. Gated on
  // `isActive`, exactly like DatasetSplitStep's own push: this component
  // stays mounted (hidden via CSS, not unmounted) once reached, and its state
  // keeps changing in the background — a converter's poll resolving calls
  // refreshSession, which updates `session`/`columnTypes`/`isApplying` and
  // re-runs this effect. Without the gate, that would silently replace
  // step 0's SplitDatasetRows if the user had already clicked "Atrás". The
  // slot is yielded by the previous run's cleanup below, and `isActive` is in
  // the deps so it's reclaimed on the way back in.
  useEffect(() => {
    if (!isActive) return;
    setSessionRightContent(
      session ? (
        <SessionConvertersRightBar
          session={session}
          inputColumnNames={newExp.input_columns}
          columnTypes={columnTypes}
          onConvertersChanged={refreshSession}
          onApplyStart={handleApplyStart}
          isApplying={isApplying}
        />
      ) : (
        <Box
          sx={{
            display: "flex",
            height: "100%",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <CircularProgress size={24} />
        </Box>
      ),
    );
    return () => setSessionRightContent(null);
  }, [
    session,
    newExp.input_columns,
    columnTypes,
    refreshSession,
    handleApplyStart,
    isApplying,
    setSessionRightContent,
    isActive,
  ]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" component="h1">
          {t("models:label.sessionConverters")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("models:label.sessionConvertersDescription")}
        </Typography>
      </Box>
      <Box
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        sx={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          pt: 2,
          position: "relative",
          outline: isDragOver
            ? `2px dashed ${theme.palette.primary.main}`
            : isDragging
              ? `2px dashed ${theme.palette.divider}`
              : "none",
          transition: "outline 0.15s",
        }}
      >
        {isDragging && (
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              zIndex: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: isDragOver
                ? `${theme.palette.primary.main}14`
                : theme.palette.action.hover,
              pointerEvents: "none",
              transition: "background-color 0.15s",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color: isDragOver
                  ? theme.palette.primary.main
                  : theme.palette.text.secondary,
                fontWeight: 600,
                pointerEvents: "none",
                transition: "color 0.15s",
              }}
            >
              {t("datasets:label.dropToolHere")}
            </Typography>
          </Box>
        )}
        {session ? (
          <AppliedConvertersView
            session={session}
            isApplying={isApplying}
            onRemoveConverter={handleRemoveConverter}
            columnTypes={columnTypes}
          />
        ) : (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              py: 8,
            }}
          >
            <CircularProgress />
          </Box>
        )}
      </Box>
      <StepperNavigationFooter
        onBack={onBack}
        onNext={onCreateSession}
        // Re-review gap (b): advancing mid-apply can land inside the
        // preprocessing job's rmtree window, where both
        // preprocessed-columns and validation silently fall back to the
        // raw dataset — seeding/validating a selection that stale disk
        // state will not actually have once the apply finishes.
        nextDisabled={isApplying}
      />
    </Box>
  );
}

PreprocessingStep.propTypes = {
  newExp: PropTypes.shape({
    input_columns: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  dataset: PropTypes.object.isRequired,
  modelSessionId: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    .isRequired,
  refreshTrigger: PropTypes.number.isRequired,
  isActive: PropTypes.bool,
  onBack: PropTypes.func.isRequired,
  onCreateSession: PropTypes.func.isRequired,
};

export default PreprocessingStep;
