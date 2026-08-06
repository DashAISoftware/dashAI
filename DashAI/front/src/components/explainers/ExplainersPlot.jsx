import { React, useEffect, useState } from "react";
import { CircularProgress, Box } from "@mui/material";
import PropTypes from "prop-types";
import { useSnackbar } from "notistack";

import { getExplainerPlot as getExplainerPlotRequest } from "../../api/explainer";
import { useTranslation } from "react-i18next";
import ArtifactViewer from "../shared/ArtifactViewer";
import ExplainerInstanceTable from "./ExplainerInstanceTable";

/** Wrap legacy plotly JSON strings as plotly artifacts; pass typed dicts through. */
function parseExplanationArtifacts(items) {
  return items.map((item) =>
    typeof item === "string"
      ? { type: "plotly", payload: item, title: null, role: "explanation" }
      : item,
  );
}

/** Build the onSaveEdit/onResetEdit/canReset props shared by every leaf. */
function leafProps(
  artifact,
  { onSaveOverride, onResetOverride, overriddenIndexes },
) {
  return {
    canReset: overriddenIndexes.includes(artifact.index),
    onSaveEdit: onSaveOverride
      ? (figure) => onSaveOverride(artifact.index, figure)
      : null,
    onResetEdit: onResetOverride ? () => onResetOverride(artifact.index) : null,
  };
}

/**
 * Lay out a batch of leaf artifacts: the first artifact fills the row beside
 * whatever `leading` element is passed (a selector, or nothing); any further
 * artifacts stack below at full width, most recent first. `siblings` is the
 * full artifact list of the batch so the fullscreen viewer can navigate
 * between them.
 */
function ArtifactBatch({
  artifacts,
  siblings,
  ctx,
  leading = null,
  leadingFlex,
  leadingMinWidth = 0,
  siblingOffset = 0,
}) {
  // Key by position within the batch, not by artifact.index: switching the
  // selected group then reuses the same viewer/Plot instance at each slot and
  // updates it in place (Plotly diffs) instead of unmounting the tall old plot
  // and mounting a new one, which briefly collapses page height and makes the
  // window scroll up.
  //
  // siblingIndex maps this leaf into `siblings` (which may span every group,
  // not just this batch) via siblingOffset, so the fullscreen viewer can page
  // across groups even when each group has a single artifact.
  const renderLeaf = (artifact, i) => (
    <ArtifactViewer
      key={i}
      artifact={artifact}
      siblingArtifacts={siblings}
      siblingIndex={siblingOffset + i}
      {...leafProps(artifact, ctx)}
    />
  );

  const [firstArtifact, ...rest] = artifacts;
  const stacked = rest.map((artifact, i) => ({ artifact, i: i + 1 })).reverse();

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", gap: 3, width: "100%" }}
    >
      <Box sx={{ display: "flex", gap: 3, alignItems: "stretch" }}>
        {leading && (
          <Box
            sx={{
              flex: leadingFlex,
              minWidth: leadingMinWidth,
              // Flex + stretch so the leading element (a table whose root is
              // height:100%) fills this cell and matches the first artifact's
              // height instead of collapsing to its own content.
              display: "flex",
              minHeight: 0,
            }}
          >
            {leading}
          </Box>
        )}
        <Box sx={{ flex: 1, minWidth: 0 }}>{renderLeaf(firstArtifact, 0)}</Box>
      </Box>
      {stacked.map(({ artifact, i }) => renderLeaf(artifact, i))}
    </Box>
  );
}

ArtifactBatch.propTypes = {
  artifacts: PropTypes.array.isRequired,
  siblings: PropTypes.array.isRequired,
  ctx: PropTypes.object.isRequired,
  leading: PropTypes.node,
  leadingFlex: PropTypes.string,
  leadingMinWidth: PropTypes.number,
  siblingOffset: PropTypes.number,
};

/**
 * Story for one explained instance (local explainers only). Generated
 * automatically as part of the explainer job - this only displays it, the
 * same box used for every other text artifact.
 */
function InstanceStoryBox({ story }) {
  if (!story) return null;
  return (
    <Box sx={{ width: "100%" }}>
      <ArtifactViewer artifact={{ type: "text", payload: story }} />
    </Box>
  );
}

InstanceStoryBox.propTypes = {
  story: PropTypes.string,
};

/**
 * Render a GroupedArtifacts item: a selector listing every group, beside the
 * selected group's first artifact (with the rest stacked below). Holds its own
 * selection state, so multiple selectors on one card are independent.
 *
 * The selector widget depends on `datasetPath`: local explainers pass the
 * explained rows dataset path so the picker shows the actual instance feature
 * values (the row index selects the group); global explainers omit it and get
 * a plain title list.
 *
 * `story` (optional) looks up the per-instance story text: only passed for
 * local explainers whose explainer type supports it.
 */
function GroupedArtifactsView({
  grouped,
  ctx,
  datasetPath = null,
  selected: selectedProp = null,
  onSelect = null,
  story = null,
}) {
  const { t } = useTranslation(["explainers"]);
  const [localSelected, setLocalSelected] = useState(0);
  const selected = selectedProp ?? localSelected;
  const setSelected = onSelect ?? setLocalSelected;
  const groups = grouped.groups ?? [];
  if (groups.length === 0) return null;

  const group = groups[selected] ?? groups[0];
  const titles = groups.map(
    (g, i) =>
      g.title ?? t("explainers:label.instanceNumber", { number: i + 1 }),
  );
  const wide = Boolean(datasetPath);

  // When the story box is shown, it takes over the space of any pre-existing
  // text artifact (e.g. ContrastiveShap's plot already carries the same
  // sentence as a caption) instead of showing both. Falls back to the
  // unfiltered list if a group has nothing left after dropping its text
  // artifact(s), so a text-only group never renders empty.
  const dropCaption = Boolean(story);
  const displayedArtifacts = (arts) => {
    if (!dropCaption) return arts;
    const withoutText = arts.filter((a) => a.type !== "text");
    return withoutText.length > 0 ? withoutText : arts;
  };

  // Fullscreen navigation spans every group's artifacts (flattened), so the
  // viewer can page across groups even when each group has a single artifact.
  // The selected group's artifacts occupy the slice starting at `offset`.
  const allArtifacts = groups.flatMap((g) => displayedArtifacts(g.artifacts));
  const offset = groups
    .slice(0, selected)
    .reduce((n, g) => n + displayedArtifacts(g.artifacts).length, 0);

  // Rendered directly (no height cap): ExplainerInstanceTable's root is
  // height:100%, so it fills the stretched batch cell and matches the height
  // of the first artifact beside it, scrolling internally when long.
  const selector = (
    <ExplainerInstanceTable
      datasetPath={datasetPath}
      titles={titles}
      selectedIndex={selected}
      onSelect={setSelected}
    />
  );

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", gap: 1, width: "100%" }}
    >
      <ArtifactBatch
        artifacts={displayedArtifacts(group.artifacts)}
        siblings={allArtifacts}
        siblingOffset={offset}
        ctx={ctx}
        leading={selector}
        leadingFlex={wide ? "0 0 46%" : "0 0 25%"}
        leadingMinWidth={wide ? 320 : 220}
      />
      {story && <InstanceStoryBox story={story.getStory(selected)} />}
    </Box>
  );
}

GroupedArtifactsView.propTypes = {
  grouped: PropTypes.object.isRequired,
  ctx: PropTypes.object.isRequired,
  datasetPath: PropTypes.string,
  selected: PropTypes.number,
  onSelect: PropTypes.func,
  story: PropTypes.shape({
    getStory: PropTypes.func.isRequired,
  }),
};

/**
 * Render one top level response item: a "grouped" selector
 * (`GroupedArtifactsView`) or a plain leaf artifact (shown alone at full
 * width). `datasetPath` is forwarded to grouped items so local explainers get
 * the dataset row picker.
 */
function renderItem(
  item,
  ctx,
  datasetPath = null,
  selection = null,
  story = null,
) {
  if (item.type === "grouped") {
    return (
      <GroupedArtifactsView
        grouped={item}
        ctx={ctx}
        datasetPath={datasetPath}
        selected={selection ? selection.selected : null}
        onSelect={selection ? selection.onSelect : null}
        story={story}
      />
    );
  }
  return <ArtifactViewer artifact={item} {...leafProps(item, ctx)} />;
}

export default function ExplainersPlot({
  explainer,
  scope,
  supportsStory = false,
  onSaveOverride = null,
  onResetOverride = null,
  overriddenIndexes = [],
  cacheEntry = null,
  onCacheUpdate = null,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const cachedItems = cacheEntry ? cacheEntry.items : null;
  const [items, setItems] = useState(() => cachedItems ?? []);
  const [loading, setLoading] = useState(() => cachedItems == null);
  const { t } = useTranslation(["explainers"]);
  const isLocal = scope === "local";
  const datasetPath = isLocal ? explainer.input_dataset_path : null;

  const storyProps =
    isLocal && supportsStory
      ? {
          getStory: (groupIndex) =>
            explainer.stories?.[String(groupIndex)] ?? null,
        }
      : null;

  const getExplainerPlot = async () => {
    setLoading(true);
    try {
      const response = await getExplainerPlotRequest(explainer.id, scope);
      if (!response || response.length === 0) {
        setItems([]);
        if (onCacheUpdate) onCacheUpdate({ items: [] });
        enqueueSnackbar(t("explainers:error.noData"), { variant: "warning" });
      } else {
        const parsed = parseExplanationArtifacts(response);
        setItems(parsed);
        if (onCacheUpdate) onCacheUpdate({ items: parsed });
      }
    } catch (error) {
      setItems([]);
      if (onCacheUpdate) onCacheUpdate({ items: [] });
      enqueueSnackbar(t("explainers:error.fetchExplainers"), {
        variant: "error",
      });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (explainer.status !== 3) return;
    // Cache hit: reuse fetched artifacts, skip the network entirely so a card
    // scrolled back into view does not refetch.
    if (cacheEntry && cacheEntry.items != null) {
      setItems(cacheEntry.items);
      setLoading(false);
      return;
    }
    getExplainerPlot();
  }, [explainer.id, explainer.status, scope]);

  if (loading || explainer.status !== 3) {
    if (explainer.status === 4) {
      return <Box sx={{ p: 4 }}>{t("explainers:error.explainerFailed")}</Box>;
    }
    return (
      <Box sx={{ display: "flex", justifyContent: "flex-start", p: 2 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (items.length === 0) {
    return <Box sx={{ p: 2 }}>{t("explainers:error.noData")}</Box>;
  }

  const ctx = { onSaveOverride, onResetOverride, overriddenIndexes };

  // Every top level item renders continuously: a plain artifact at full width,
  // a "grouped" item as its own self contained selector. Local explainers pass
  // the explained rows dataset path so their grouped selector shows the
  // instance feature values instead of plain labels.
  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", gap: 3, width: "100%" }}
    >
      {items.map((item, i) => (
        <Box key={i}>
          {renderItem(
            item,
            ctx,
            datasetPath,
            {
              selected: cacheEntry
                ? (cacheEntry.selectedGroups?.[i] ?? 0)
                : null,
              onSelect: onCacheUpdate
                ? (value) =>
                    onCacheUpdate({
                      selectedGroups: {
                        ...(cacheEntry?.selectedGroups ?? {}),
                        [i]: value,
                      },
                    })
                : null,
            },
            storyProps,
          )}
        </Box>
      ))}
    </Box>
  );
}

ExplainersPlot.propTypes = {
  explainer: PropTypes.shape({
    id: PropTypes.number,
    run_id: PropTypes.number,
    status: PropTypes.number,
    input_dataset_path: PropTypes.string,
    stories: PropTypes.object,
  }).isRequired,
  scope: PropTypes.string.isRequired,
  supportsStory: PropTypes.bool,
  onSaveOverride: PropTypes.func,
  onResetOverride: PropTypes.func,
  overriddenIndexes: PropTypes.arrayOf(PropTypes.number),
  cacheEntry: PropTypes.shape({
    items: PropTypes.array,
    selectedGroups: PropTypes.object,
  }),
  onCacheUpdate: PropTypes.func,
};
