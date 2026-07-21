import React, {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
} from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Button,
  Chip,
  Stack,
  Collapse,
  Tabs,
  Tab,
  Divider,
  Grid,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  ToggleButtonGroup,
  ToggleButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Close as CloseIcon,
  Dataset as DatasetIcon,
  EditNote as EditNoteIcon,
} from "@mui/icons-material";
import ExplainersCard from "../explainers/ExplainersCard";
import PredictionCard from "./PredictionCard";
import { LoadingButton } from "@mui/lab";
import DatasetPredictionPanel from "./DatasetPredictionPanel";
import ManualPredictionPanel from "./ManualPredictionPanel";
import LiveMetricsChart from "./LiveMetricsChart";
import HyperparameterPlots from "./HyperparameterPlots";
import { getExplainers } from "../../api/explainer";
import { getComponents } from "../../api/component";
import { getPredictions } from "../../api/predict";
import { getModelSessionById } from "../../api/modelSession";
import { getDatasetSample } from "../../api/datasets";
import { checkHowManyOptimazers } from "../../utils/schema";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useModels } from "./ModelsContext";
import { Virtuoso } from "react-virtuoso";

// Stable reference returned for cache misses.
const EMPTY_EXPLAINER_ENTRY = {
  items: null,
  overriddenIndexes: [],
  selectedGroups: {},
};

// Fallback placeholder height before a card has ever been measured.
const DEFAULT_CARD_HEIGHT = 520;

// Key includes the explainer type and creation time, not just the id: on
// retrain the backend reuses low ids, so a new explainer must not inherit a
// deleted one's cached plot.
const explainerCacheKey = (scope, e) =>
  `${scope}-${e.id}-${e.explainer_name ?? ""}-${e.created ?? ""}`;

// IntersectionObserver margin (top right bottom left) for when a card mounts
// its plot. Bigger on top so cards render before entering view when scrolling
// up, so their height has settled and does not cause a correction that tears.
const CARD_PRELOAD_MARGIN = "900px 0px 400px 0px";

/**
 * Renders a card once it nears the viewport, then keeps it mounted (latched),
 * so each plot is created at most once. A box sized to the last measured height
 * holds space until then. Memoized with stable props so unrelated RunResults
 * renders do not restart Plotly. The cache makes the eventual unmount lossless.
 */
const LazyExplainerCard = React.memo(function LazyExplainerCard({
  scrollRoot,
  heightsRef,
  cacheKey,
  explainer,
  scope,
  displayName,
  onDelete,
  cacheEntry,
  updateCacheEntry,
  isHighlighted,
}) {
  const nodeRef = useRef(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = nodeRef.current;
    // Once shown, latch: stop observing and never unmount the plot.
    if (!node || shown) return undefined;
    // Give the plot a head start before it scrolls in. Kept within the list's
    // increaseViewportBy so the item is already in the DOM when this fires.
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setShown(true);
      },
      { root: scrollRoot ?? null, rootMargin: CARD_PRELOAD_MARGIN },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [scrollRoot, shown]);

  useEffect(() => {
    const node = nodeRef.current;
    if (!shown || !node) return undefined;
    const record = () => {
      heightsRef.current[cacheKey] = node.offsetHeight;
    };
    record();
    const observer = new ResizeObserver(record);
    observer.observe(node);
    return () => observer.disconnect();
  }, [shown, cacheKey, heightsRef]);

  const onCacheUpdate = useCallback(
    (patch) => updateCacheEntry(cacheKey, patch),
    [updateCacheEntry, cacheKey],
  );

  const knownHeight = heightsRef.current[cacheKey];
  return (
    <Box
      ref={nodeRef}
      sx={{
        minHeight: shown ? undefined : (knownHeight ?? DEFAULT_CARD_HEIGHT),
        // Own compositor layer so the scroller composites the painted plot
        // instead of repainting heavy Plotly content each frame (which tears).
        // No paint containment: it would clip the highlight ring.
        ...(shown && { transform: "translateZ(0)" }),
      }}
    >
      {shown ? (
        <ExplainersCard
          explainer={explainer}
          scope={scope}
          displayName={displayName}
          onDelete={onDelete}
          cacheEntry={cacheEntry}
          onCacheUpdate={onCacheUpdate}
          isHighlighted={isHighlighted}
          compact
        />
      ) : null}
    </Box>
  );
});

LazyExplainerCard.propTypes = {
  scrollRoot: PropTypes.instanceOf(Element),
  heightsRef: PropTypes.shape({ current: PropTypes.object }).isRequired,
  cacheKey: PropTypes.string.isRequired,
  explainer: PropTypes.object.isRequired,
  scope: PropTypes.string.isRequired,
  displayName: PropTypes.string,
  onDelete: PropTypes.func,
  cacheEntry: PropTypes.object,
  updateCacheEntry: PropTypes.func.isRequired,
  isHighlighted: PropTypes.bool,
};

export default function RunResults({
  run,
  session,
  onRefresh,
  explainerRefreshTrigger,
  resultsVisible: controlledVisible = undefined,
  setResultsVisible: setControlledVisible = undefined,
  autoExpand = false,
  fillHeight = false,
  profiles,
  selectedProfile,
  onProfileChange,
}) {
  const isControlled = controlledVisible !== undefined;

  const [globalExplainers, setGlobalExplainers] = useState([]);
  const [localExplainers, setLocalExplainers] = useState([]);
  const [predictions, setPredictions] = useState([]);

  // "Prediction #N" counts only this run's own predictions, numbered per
  // section (Dataset vs Manual) in creation order, not `prediction.id`, which
  // is a database wide key shared across every run and session.
  const predictionDisplayNumbers = useMemo(() => {
    const numbers = new Map();
    [
      predictions.filter((p) => p.dataset_id),
      predictions.filter((p) => !p.dataset_id),
    ].forEach((group) => {
      [...group]
        .sort((a, b) => a.id - b.id)
        .forEach((p, index) => numbers.set(p.id, index + 1));
    });
    return numbers;
  }, [predictions]);
  const [internalVisible, setInternalVisible] = useState(() => {
    if (run.status === 0) return false;
    const saved = localStorage.getItem(`run-${run.id}-results-visible`);
    return saved ? JSON.parse(saved) : false;
  });
  const resultsVisible = isControlled ? controlledVisible : internalVisible;
  const setResultsVisible = isControlled
    ? setControlledVisible
    : setInternalVisible;

  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem(`run-${run.id}-active-tab`);
    if (saved !== null) {
      const savedTab = JSON.parse(saved);
      // Tabs 1+ (Explainability, Predictions, Hyperparameters) require a finished run
      if (savedTab > 0 && run.status !== 3) return 0;
      return savedTab;
    }
    return 0;
  });

  const [trainingDatasetSample, setTrainingDatasetSample] = useState(null);
  const [outputColumn, setOutputColumn] = useState(null);

  const [datasetExpanded, setDatasetExpanded] = useState(true);
  const [manualExpanded, setManualExpanded] = useState(true);
  // "global" | "local",  which explainer scope is shown
  const [explainerFilter, setExplainerFilter] = useState("global");
  // Detail view scroll container, kept in state so Virtuoso receives it as
  // customScrollParent. followOutput and initialTopMostItemIndex handle the
  // bottom anchoring.
  const [explainerScrollParent, setExplainerScrollParent] = useState(null);
  // Handle on the virtualized list, used to scroll a new explainer into view.
  const virtuosoRef = useRef(null);
  // A just added explainer: newExplainerKey triggers the scroll and flash;
  // highlightedExplainerKey drives the ring animation.
  const [newExplainerKey, setNewExplainerKey] = useState(null);
  const [highlightedExplainerKey, setHighlightedExplainerKey] = useState(null);
  // Last measured height per card key, so placeholders reserve exact space.
  const cardHeightsRef = useRef({});
  // Explainer keys seen on the previous fetch; null until the first load so
  // the initial batch is not treated as newly added.
  const seenExplainerKeysRef = useRef(null);
  // Explainer component name to display name, fetched once and shared so cards
  // do not each fetch it (a per card fetch shifted heights).
  const [explainerDisplayNames, setExplainerDisplayNames] = useState({});
  // Per card plot state (items, edits, selection), so the list can unmount
  // offscreen cards without refetching or losing edits. Survives because
  // RunResults stays mounted.
  const [explainerCache, setExplainerCache] = useState({});
  const getCacheEntry = useCallback(
    (key) => explainerCache[key] ?? EMPTY_EXPLAINER_ENTRY,
    [explainerCache],
  );
  const updateCacheEntry = useCallback((key, patch) => {
    setExplainerCache((prev) => ({
      ...prev,
      [key]: { ...(prev[key] ?? EMPTY_EXPLAINER_ENTRY), ...patch },
    }));
  }, []);
  // "dataset" | "manual",  which prediction section is shown
  const [predictionFilter, setPredictionFilter] = useState("dataset");
  const [showDatasetPanel, setShowDatasetPanel] = useState(false);
  const datasetRunRef = useRef(null);
  const [datasetRunState, setDatasetRunState] = useState({
    canRun: false,
    isSubmitting: false,
  });
  const [showManualPanel, setShowManualPanel] = useState(false);
  const manualSaveRef = useRef(null);
  const [manualSaveState, setManualSaveState] = useState({
    canSave: false,
    isSaving: false,
  });

  const optimizables = checkHowManyOptimazers({ params: run.parameters });
  const isFinished = run.status === 3;
  const isRunning = run.status === 1 || run.status === 2;
  const { t } = useTranslation(["models", "common"]);
  const theme = useTheme();

  // Explains *why* a tab is disabled, so it reads as a real (if currently
  // unavailable) tab rather than being confused with the static group labels.
  const notFinishedTooltip = !isFinished
    ? t("models:message.tabAvailableAfterFinish")
    : "";
  const hyperparametersTooltip = !isFinished
    ? notFinishedTooltip
    : optimizables === 0
      ? t("models:message.noOptimizableParamsForHpo")
      : "";

  // Same "pill bar" tab styling used in DatasetVisualization, so both
  // sections of the app read as one consistent tab component.
  const pillTabsSx = {
    minHeight: 40,
    bgcolor: theme.palette.ui.box,
    borderRadius: 1,
    "& .MuiTabs-indicator": { height: "2px" },
    "& .MuiTab-root": {
      minHeight: 40,
      fontSize: "0.85rem",
      borderRadius: "4px",
      transition: "all 0.2s",
      border: "1px solid transparent",
      textTransform: "none",
      "&:hover": { bgcolor: theme.palette.action.hover },
      "&.Mui-disabled": {
        color: theme.palette.text.disabled,
        bgcolor: theme.palette.ui.disabled,
        borderColor: theme.palette.ui.border,
        opacity: 0.6,
        cursor: "not-allowed",
        filter: "grayscale(0.6)",
        position: "relative",
        "&::after": {
          content: '""',
          position: "absolute",
          inset: 0,
          borderRadius: "4px",
          pointerEvents: "none",
          background:
            "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.1) 10px, rgba(0,0,0,0.1) 20px)",
        },
      },
    },
  };

  // Same pill bar styling as pillTabsSx, with the selected fill toned down so
  // it reads as a secondary in page filter.
  const pillToggleSx = {
    minHeight: 40,
    bgcolor: theme.palette.ui.box,
    borderRadius: 1,
    "& .MuiToggleButtonGroup-grouped": {
      minHeight: 40,
      fontSize: "0.85rem",
      fontWeight: 400,
      textTransform: "none",
      border: "1px solid transparent",
      borderRadius: "4px !important",
      color: "text.secondary",
      "&:hover": { bgcolor: theme.palette.action.hover },
      "&.Mui-selected": {
        bgcolor: "background.paper",
        color: "primary.main",
        fontWeight: 600,
        borderBottom: `2px solid ${theme.palette.primary.main}`,
        "&:hover": { bgcolor: "background.paper" },
      },
    },
  };

  const runId = run.id;
  const fetchOperations = useCallback(async () => {
    if (!runId) return;

    try {
      const [globalExpls, localExpls, preds] = await Promise.all([
        getExplainers(runId, "global").catch(() => []),
        getExplainers(runId, "local").catch(() => []),
        getPredictions(runId).catch(() => []),
      ]);

      // Detect explainers added since the last fetch. First fetch seeds the
      // baseline; later fetches switch the scope toggle to the new explainer.
      const currentKeys = new Set([
        ...globalExpls.map((e) => `global-${e.id}`),
        ...localExpls.map((e) => `local-${e.id}`),
      ]);
      if (seenExplainerKeysRef.current === null) {
        seenExplainerKeysRef.current = currentKeys;
      } else {
        const added = [...currentKeys].filter(
          (key) => !seenExplainerKeysRef.current.has(key),
        );
        seenExplainerKeysRef.current = currentKeys;
        if (added.length > 0) {
          const key = added[added.length - 1];
          setExplainerFilter(key.startsWith("global-") ? "global" : "local");
          setNewExplainerKey(key);
        }
      }

      setGlobalExplainers(globalExpls);
      setLocalExplainers(localExpls);
      setPredictions(preds);

      // Drop cached state for explainers that no longer exist (deleted on
      // retrain), so the cache cannot grow or serve a stale entry.
      const validKeys = new Set([
        ...globalExpls.map((e) => explainerCacheKey("global", e)),
        ...localExpls.map((e) => explainerCacheKey("local", e)),
      ]);
      setExplainerCache((prev) => {
        const next = {};
        let removed = false;
        Object.keys(prev).forEach((key) => {
          if (validKeys.has(key)) next[key] = prev[key];
          else removed = true;
        });
        return removed ? next : prev;
      });
    } catch (error) {
      console.error("Error fetching operations:", error);
    }
  }, [runId]);

  useEffect(() => {
    fetchOperations();
  }, [fetchOperations, explainerRefreshTrigger]);

  // Fetch explainer display names once and share them with every card.
  useEffect(() => {
    getComponents({ selectTypes: ["GlobalExplainer", "LocalExplainer"] })
      .then((components) => {
        const names = {};
        components.forEach((component) => {
          names[component.name] = component.display_name || component.name;
        });
        setExplainerDisplayNames(names);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const sessionId = run.model_session_id || session?.id;
    if (!sessionId) return;
    let cancelled = false;
    getModelSessionById(sessionId)
      .then((sessionData) => {
        if (cancelled) return null;
        setOutputColumn(sessionData.output_columns?.[0] ?? null);
        return getDatasetSample(sessionData.dataset_id);
      })
      .then((sample) => {
        if (!cancelled && sample) setTrainingDatasetSample(sample);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [run.model_session_id, session?.id]);

  // Refetch when run parameters change (after editing)
  useEffect(() => {
    fetchOperations();
  }, [
    run.parameters,
    run.optimizer_parameters,
    run.goal_metric,
    fetchOperations,
  ]);

  const hasRunningExplainers =
    globalExplainers.some((e) => e.status === 1 || e.status === 2) ||
    localExplainers.some((e) => e.status === 1 || e.status === 2);

  // Explainers shown under the current scope toggle (global / local).
  const activeExplainers =
    explainerFilter === "global" ? globalExplainers : localExplainers;

  // Read in the deferred callback so it sees the list after the scope switch.
  const activeExplainersRef = useRef(activeExplainers);
  useEffect(() => {
    activeExplainersRef.current = activeExplainers;
  }, [activeExplainers]);

  useEffect(() => {
    if (!hasRunningExplainers) return;
    const interval = setInterval(fetchOperations, 3000);
    return () => clearInterval(interval);
  }, [hasRunningExplainers, fetchOperations]);

  // Scroll a new explainer card into view and flash it, like the notebooks
  // view. The delay lets the scope switch settle before scrolling.
  useEffect(() => {
    if (!newExplainerKey) return undefined;
    const scrollTimer = setTimeout(() => {
      const list = activeExplainersRef.current;
      const scope = newExplainerKey.startsWith("global-") ? "global" : "local";
      const id = Number(newExplainerKey.slice(scope.length + 1));
      const index = list.findIndex((e) => e.id === id);
      const targetIndex = index >= 0 ? index : list.length - 1;
      if (virtuosoRef.current && targetIndex >= 0) {
        // align end, not center: a new explainer is appended last, so pinning
        // its bottom lands the scroller fully down; followOutput holds it as
        // the plot loads and the card grows.
        virtuosoRef.current.scrollToIndex({
          index: targetIndex,
          align: "end",
          behavior: "smooth",
        });
      }
      setHighlightedExplainerKey(newExplainerKey);
      setNewExplainerKey(null);
    }, 100);
    return () => clearTimeout(scrollTimer);
  }, [newExplainerKey]);

  // Clear the highlight after the animation, in its own effect so the
  // setNewExplainerKey(null) above cannot cancel this timer (else the card
  // stays flagged and the ring replays on every remount, e.g. tab switch).
  useEffect(() => {
    if (!highlightedExplainerKey) return undefined;
    const timer = setTimeout(() => setHighlightedExplainerKey(null), 4000);
    return () => clearTimeout(timer);
  }, [highlightedExplainerKey]);

  useEffect(() => {
    const handleOpenDialog = (event) => {
      if (event.detail.runId === run.id) {
        setResultsVisible(true);
        setActiveTab(2);
        setShowDatasetPanel(true);
      }
    };
    window.addEventListener("openPredictionDialog", handleOpenDialog);
    return () =>
      window.removeEventListener("openPredictionDialog", handleOpenDialog);
  }, [run.id]);

  useEffect(() => {
    if (isRunning && autoExpand) {
      setResultsVisible(true);
      setActiveTab(0); // Live Metrics tab
    }
  }, [isRunning, autoExpand]);

  useEffect(() => {
    if (isControlled) return;
    localStorage.setItem(
      `run-${run.id}-results-visible`,
      JSON.stringify(resultsVisible),
    );
  }, [resultsVisible, run.id, isControlled]);

  useEffect(() => {
    localStorage.setItem(`run-${run.id}-active-tab`, JSON.stringify(activeTab));
  }, [activeTab, run.id]);

  // Expose the active tab while this run is shown full screen, so the right
  // sidebar can swap its content (e.g. list explainers on the explainers tab).
  const params = useParams();
  const modelsContext = useModels();
  const setRunDetailTab = modelsContext?.setRunDetailTab;
  const isDetailView = String(params.runId ?? "") === String(run.id);
  useEffect(() => {
    if (!isDetailView || !setRunDetailTab) return;
    setRunDetailTab(activeTab);
    return () => setRunDetailTab(null);
  }, [isDetailView, activeTab, setRunDetailTab]);

  const handlePredictionCreated = (prediction) => {
    if (prediction) {
      setPredictions((prev) => {
        const index = prev.findIndex((p) => p.id === prediction.id);
        if (index === -1) {
          return [prediction, ...prev];
        }

        const updated = [...prev];
        updated[index] = prediction;
        return updated;
      });
    } else {
      fetchOperations();
    }

    if (onRefresh) onRefresh();
  };

  // Stable so memoized cards keep their identity across RunResults renders
  // (e.g. the 3s poll) instead of rerendering and restarting Plotly.
  const handleExplainerDeleted = useCallback(() => {
    fetchOperations();
    if (onRefresh) onRefresh();
  }, [fetchOperations, onRefresh]);

  const handlePredictionDeleted = () => {
    fetchOperations();
    if (onRefresh) onRefresh();
  };

  const totalOperations =
    globalExplainers.length + localExplainers.length + predictions.length;

  const tabsHeader = (
    <Box
      sx={{
        display: "flex",
        alignItems: "flex-end",
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            textTransform: "uppercase",
            letterSpacing: 0.5,
            fontWeight: 600,
            pl: 2,
            pt: 1,
          }}
        >
          {t("models:label.metrics")}
        </Typography>
        <Tabs
          value={[0, 3].includes(activeTab) ? activeTab : false}
          onChange={(e, newValue) => setActiveTab(newValue)}
          aria-label="Result characteristics tabs"
          sx={pillTabsSx}
        >
          <Tab value={0} label={t("models:label.liveMetrics")} />
          <Tab
            value={3}
            label={
              <Tooltip title={hyperparametersTooltip}>
                <span style={{ pointerEvents: "auto" }}>
                  {t("models:label.hyperparameters")}
                </span>
              </Tooltip>
            }
            disabled={!isFinished || optimizables === 0}
          />
        </Tabs>
      </Box>

      {/* Empty spacer just for the horizontal gap between groups. Kept
              out of the flex height/alignment calculation so the actual
              rule (positioned absolutely inside it) can be sized freely
              without pushing the tabs around. */}
      <Box
        sx={{
          position: "relative",
          alignSelf: "stretch",
          width: 0,
          mx: 4,
        }}
      >
        <Box
          sx={{
            position: "absolute",
            top: 32,
            bottom: -16,
            left: 0,
            width: "1px",
            bgcolor: "divider",
          }}
        />
      </Box>

      <Box sx={{ display: "flex", flexDirection: "column" }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            textTransform: "uppercase",
            letterSpacing: 0.5,
            fontWeight: 600,
            pl: 2,
            pt: 1,
          }}
        >
          {t("models:label.operations")}
        </Typography>
        <Tabs
          value={[1, 2].includes(activeTab) ? activeTab : false}
          onChange={(e, newValue) => setActiveTab(newValue)}
          aria-label="Result operations tabs"
          sx={pillTabsSx}
        >
          <Tab
            value={1}
            label={
              <Tooltip title={notFinishedTooltip}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    pointerEvents: "auto",
                  }}
                >
                  <span>{t("models:label.explainability")}</span>
                  {isFinished && (
                    <Chip
                      label={globalExplainers.length + localExplainers.length}
                      size="small"
                      color="primary"
                    />
                  )}
                </Box>
              </Tooltip>
            }
            disabled={!isFinished}
          />
          <Tab
            value={2}
            label={
              <Tooltip title={notFinishedTooltip}>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 2,
                    pointerEvents: "auto",
                  }}
                >
                  <span>{t("models:label.predictions")}</span>
                  {isFinished && (
                    <Chip
                      label={predictions.length}
                      size="small"
                      color="primary"
                    />
                  )}
                </Box>
              </Tooltip>
            }
            disabled={!isFinished}
          />
        </Tabs>
      </Box>

      {/* Scope selector, shown only on the Explainability tab. Pushed right so
          it reads as a filter on the tab, not a third tab group. */}
      {activeTab === 1 && isFinished && (
        <Box
          sx={{
            ml: "auto",
            display: "flex",
            alignItems: "flex-end",
            alignSelf: "flex-end",
          }}
        >
          <ToggleButtonGroup
            value={explainerFilter}
            exclusive
            onChange={(e, newValue) => {
              if (newValue !== null) setExplainerFilter(newValue);
            }}
            sx={pillToggleSx}
          >
            <ToggleButton value="global" sx={{ px: 1.5 }}>
              {t("models:label.globalExplainers")}
            </ToggleButton>
            <ToggleButton value="local" sx={{ px: 1.5 }}>
              {t("models:label.localExplainers")}
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      )}
    </Box>
  );

  const tabContent = (
    <>
      {activeTab === 0 && (
        <Box sx={{ py: 4 }}>
          <LiveMetricsChart
            run={run}
            session={session}
            profiles={profiles}
            selectedProfile={selectedProfile}
            onProfileChange={onProfileChange}
          />
        </Box>
      )}

      {activeTab === 1 && isFinished && (
        <Box sx={{ py: 4, width: "100%" }}>
          {/* Scope selector (global/local) lives in the tabs header now. */}
          {activeExplainers.length === 0 ? (
            <Typography
              variant="body2"
              color="text.secondary"
              align="center"
              sx={{ py: 6 }}
            >
              {explainerFilter === "global"
                ? t("models:label.noGlobalExplainersYet")
                : t("models:label.noLocalExplainersYet")}
            </Typography>
          ) : fillHeight ? (
            // Virtualize against the scroller so many plugin cards stay cheap.
            // Keyed on scope so toggling scrolls back to the bottom.
            <Virtuoso
              key={explainerFilter}
              ref={virtuosoRef}
              customScrollParent={explainerScrollParent ?? undefined}
              data={activeExplainers}
              followOutput="smooth"
              initialTopMostItemIndex={Math.max(0, activeExplainers.length - 1)}
              // Overscan margin. Must exceed CARD_PRELOAD_MARGIN so the item
              // is in the DOM before the observer shows it. defaultItemHeight
              // seeds the estimate for cards not yet measured.
              increaseViewportBy={{ top: 1000, bottom: 500 }}
              defaultItemHeight={DEFAULT_CARD_HEIGHT}
              itemContent={(index, explainer) => (
                // pb, not flex gap: virtualized items are not flex children.
                // px gives the highlight ring room so the scroller does not
                // clip its sides.
                <Box sx={{ px: 1.5, pb: 2 }}>
                  <LazyExplainerCard
                    scrollRoot={explainerScrollParent ?? undefined}
                    heightsRef={cardHeightsRef}
                    cacheKey={explainerCacheKey(explainerFilter, explainer)}
                    explainer={explainer}
                    scope={explainerFilter}
                    displayName={
                      explainerDisplayNames[explainer.explainer_name]
                    }
                    onDelete={handleExplainerDeleted}
                    cacheEntry={getCacheEntry(
                      explainerCacheKey(explainerFilter, explainer),
                    )}
                    updateCacheEntry={updateCacheEntry}
                    isHighlighted={
                      highlightedExplainerKey ===
                      `${explainerFilter}-${explainer.id}`
                    }
                  />
                </Box>
              )}
            />
          ) : (
            // Inline view: no bounded scroller, so keep the flex column. px
            // gives the highlight ring room at the sides.
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                gap: 2,
                px: 1.5,
              }}
            >
              {activeExplainers.map((explainer) => {
                const key = explainerCacheKey(explainerFilter, explainer);
                return (
                  <ExplainersCard
                    key={`${explainerFilter}-${explainer.id}`}
                    explainer={explainer}
                    scope={explainerFilter}
                    displayName={
                      explainerDisplayNames[explainer.explainer_name]
                    }
                    onDelete={handleExplainerDeleted}
                    cacheEntry={getCacheEntry(key)}
                    onCacheUpdate={(patch) => updateCacheEntry(key, patch)}
                    isHighlighted={
                      highlightedExplainerKey ===
                      `${explainerFilter}-${explainer.id}`
                    }
                    compact
                  />
                );
              })}
            </Box>
          )}
        </Box>
      )}

      {activeTab === 2 && isFinished && (
        <Box sx={{ py: 4, width: "100%" }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 2,
              mb: 4,
            }}
          >
            <ToggleButtonGroup
              value={predictionFilter}
              exclusive
              onChange={(e, newValue) => {
                if (newValue !== null) setPredictionFilter(newValue);
              }}
              sx={pillToggleSx}
            >
              <ToggleButton value="dataset" sx={{ px: 1.5 }}>
                {t("common:dataset")}
              </ToggleButton>
              <ToggleButton value="manual" sx={{ px: 1.5 }}>
                {t("models:label.manual")}
              </ToggleButton>
            </ToggleButtonGroup>

            <Box sx={{ display: "flex", gap: 2 }}>
              {predictionFilter !== "manual" && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<DatasetIcon />}
                  onClick={() => {
                    setDatasetRunState({
                      canRun: false,
                      isSubmitting: false,
                    });
                    setShowDatasetPanel(true);
                  }}
                >
                  {t("models:button.newDatasetPrediction")}
                </Button>
              )}
              {predictionFilter !== "dataset" && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<EditNoteIcon />}
                  onClick={() => {
                    setManualSaveState({ canSave: false, isSaving: false });
                    setShowManualPanel(true);
                  }}
                >
                  {t("models:button.newManualPrediction")}
                </Button>
              )}
            </Box>
          </Box>

          <Dialog
            open={showDatasetPanel}
            onClose={() => setShowDatasetPanel(false)}
            maxWidth="md"
            fullWidth
            PaperProps={{ sx: { minHeight: "500px" } }}
          >
            <DialogTitle sx={{ bgcolor: "background.paper" }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <Typography variant="h6" component="span">
                  {t("models:button.newDatasetPrediction")}
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => setShowDatasetPanel(false)}
                  sx={{ color: "text.secondary" }}
                >
                  <CloseIcon />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
              <DatasetPredictionPanel
                run={run}
                session={session}
                onSaved={(prediction) => {
                  handlePredictionCreated(prediction);
                  setShowDatasetPanel(false);
                }}
                onClose={() => setShowDatasetPanel(false)}
                runRef={datasetRunRef}
                onStateChange={setDatasetRunState}
              />
            </DialogContent>
            <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
              <Button
                variant="outlined"
                onClick={() => setShowDatasetPanel(false)}
                disabled={datasetRunState.isSubmitting}
              >
                {t("common:cancel")}
              </Button>
              <LoadingButton
                variant="contained"
                color="primary"
                disabled={!datasetRunState.canRun}
                loading={datasetRunState.isSubmitting}
                onClick={() => datasetRunRef.current?.()}
              >
                {t("prediction:button.runPrediction")}
              </LoadingButton>
            </DialogActions>
          </Dialog>

          <Dialog
            open={showManualPanel}
            onClose={() => setShowManualPanel(false)}
            maxWidth="lg"
            fullWidth
            PaperProps={{ sx: { minHeight: "500px" } }}
          >
            <DialogTitle sx={{ bgcolor: "background.paper" }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <Typography variant="h6" component="span">
                  {t("models:button.newManualPrediction")}
                </Typography>
                <IconButton
                  size="small"
                  onClick={() => setShowManualPanel(false)}
                  sx={{ color: "text.secondary" }}
                >
                  <CloseIcon />
                </IconButton>
              </Box>
            </DialogTitle>
            <DialogContent dividers sx={{ bgcolor: "background.paper" }}>
              <ManualPredictionPanel
                run={run}
                session={session}
                onSaved={(prediction) => {
                  handlePredictionCreated(prediction);
                  setShowManualPanel(false);
                }}
                onClose={() => setShowManualPanel(false)}
                saveRef={manualSaveRef}
                onStateChange={setManualSaveState}
              />
            </DialogContent>
            <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
              <Button
                variant="outlined"
                onClick={() => setShowManualPanel(false)}
                disabled={manualSaveState.isSaving}
              >
                {t("common:cancel")}
              </Button>
              <LoadingButton
                variant="contained"
                color="primary"
                disabled={!manualSaveState.canSave}
                loading={manualSaveState.isSaving}
                onClick={() => manualSaveRef.current?.()}
              >
                {t("prediction:button.saveResults")}
              </LoadingButton>
            </DialogActions>
          </Dialog>

          <Stack spacing={2}>
            {predictionFilter !== "manual" && (
              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 2,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: datasetExpanded ? 2 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <DatasetIcon fontSize="small" color="action" />
                    <Typography variant="subtitle2" fontWeight="medium">
                      {t("models:label.datasetPredictions")}
                    </Typography>
                    <Chip
                      label={predictions.filter((p) => p.dataset_id).length}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => setDatasetExpanded((prev) => !prev)}
                  >
                    {datasetExpanded ? (
                      <ExpandLessIcon fontSize="small" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" />
                    )}
                  </IconButton>
                </Box>
                <Collapse in={datasetExpanded}>
                  {predictions.filter((p) => p.dataset_id).length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      align="center"
                      sx={{ py: 3 }}
                    >
                      {t("models:label.noDatasetPredictionsYet")}
                    </Typography>
                  ) : (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(680px, 1fr))",
                        gap: 2,
                      }}
                    >
                      {predictions
                        .filter((p) => p.dataset_id)
                        .map((prediction) => (
                          <PredictionCard
                            key={prediction.id}
                            prediction={prediction}
                            onDelete={handlePredictionDeleted}
                            onUpdate={fetchOperations}
                            targetColumn={outputColumn}
                            datasetSample={trainingDatasetSample}
                            displayNumber={predictionDisplayNumbers.get(
                              prediction.id,
                            )}
                          />
                        ))}
                    </Box>
                  )}
                </Collapse>
              </Box>
            )}

            {predictionFilter !== "dataset" && (
              <Box
                sx={{
                  border: 1,
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 2,
                  width: "100%",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    mb: manualExpanded ? 2 : 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <EditNoteIcon fontSize="small" color="action" />
                    <Typography variant="subtitle2" fontWeight="medium">
                      {t("models:label.manualPredictions")}
                    </Typography>
                    <Chip
                      label={predictions.filter((p) => !p.dataset_id).length}
                      size="small"
                      color="primary"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    onClick={() => setManualExpanded((prev) => !prev)}
                  >
                    {manualExpanded ? (
                      <ExpandLessIcon fontSize="small" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" />
                    )}
                  </IconButton>
                </Box>
                <Collapse in={manualExpanded}>
                  {predictions.filter((p) => !p.dataset_id).length === 0 ? (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      align="center"
                      sx={{ py: 3 }}
                    >
                      {t("models:label.noManualPredictionsYet")}
                    </Typography>
                  ) : (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(680px, 1fr))",
                        gap: 2,
                      }}
                    >
                      {predictions
                        .filter((p) => !p.dataset_id)
                        .map((prediction) => (
                          <PredictionCard
                            key={prediction.id}
                            prediction={prediction}
                            onDelete={handlePredictionDeleted}
                            onUpdate={fetchOperations}
                            targetColumn={outputColumn}
                            datasetSample={trainingDatasetSample}
                            displayNumber={predictionDisplayNumbers.get(
                              prediction.id,
                            )}
                          />
                        ))}
                    </Box>
                  )}
                </Collapse>
              </Box>
            )}
          </Stack>
        </Box>
      )}

      {activeTab === 3 && isFinished && optimizables > 0 && (
        <Box sx={{ py: 4 }}>
          <HyperparameterPlots run={run} />
        </Box>
      )}
    </>
  );

  // Detail view: fixed header and tabs, only the content scrolls. Card list
  // view keeps the collapsible, content sized layout.
  if (fillHeight) {
    return (
      <Box
        id={`run-results-${run.id}`}
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minHeight: 0,
        }}
      >
        <Box sx={{ flexShrink: 0 }}>
          {tabsHeader}
          <Divider sx={{ my: 4 }} />
        </Box>
        <Box
          ref={setExplainerScrollParent}
          sx={{ flex: 1, minHeight: 0, overflowY: "auto" }}
        >
          {tabContent}
        </Box>
      </Box>
    );
  }

  return (
    <Box id={`run-results-${run.id}`}>
      <Collapse in={resultsVisible} timeout="auto" unmountOnExit>
        {tabsHeader}
        <Divider sx={{ my: 4 }} />
        {tabContent}
      </Collapse>
    </Box>
  );
}

RunResults.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string,
    model_name: PropTypes.string,
    status: PropTypes.number,
    experiment_id: PropTypes.number,
    parameters: PropTypes.object,
    model_session_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    test_metrics: PropTypes.object,
  }).isRequired,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  onRefresh: PropTypes.func,
  explainerRefreshTrigger: PropTypes.number,
  resultsVisible: PropTypes.bool,
  setResultsVisible: PropTypes.func,
  autoExpand: PropTypes.bool,
  fillHeight: PropTypes.bool,
  profiles: PropTypes.array,
  selectedProfile: PropTypes.string,
  onProfileChange: PropTypes.func,
};
