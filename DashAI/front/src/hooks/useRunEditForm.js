import { useState, useEffect, useMemo, useCallback } from "react";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import useSchema from "./useSchema";
import { updateRunParameters, getRunOperationsCount } from "../api/run";
import { checkIfHaveOptimazers } from "../utils/schema";

// A copy of `value` with every object's keys sorted, so two that only differ
// in key order stringify the same.
function withSortedKeys(value) {
  if (Array.isArray(value)) return value.map(withSortedKeys);
  if (value && typeof value === "object") {
    return Object.keys(value)
      .sort()
      .reduce((sorted, key) => {
        sorted[key] = withSortedKeys(value[key]);
        return sorted;
      }, {});
  }
  return value;
}

// Whether two sets of parameters run the same. The parameters form seeds
// itself with the schema defaults under the saved values, in the schema's
// order, and hands that back: a run saved without a field, or with its fields
// in another order, must not read as edited before the user changes anything.
function sameParams(edited, saved, defaults) {
  return (
    JSON.stringify(withSortedKeys({ ...defaults, ...edited })) ===
    JSON.stringify(withSortedKeys({ ...defaults, ...saved }))
  );
}

/**
 * Shared editable-parameters state/logic for a run's "Edit Run" dialog
 * (RunEditDialog), used from the compact model card, RunCard, and the model
 * detail view, so every entry point behaves identically.
 *
 * `enabled` gates the reset-on-mount and operations-count fetch: pass the
 * dialog's `open` flag so the form resets every time it reopens.
 */
export default function useRunEditForm({
  run,
  session,
  existingRuns = [],
  onRefresh,
  onSaved,
  enabled = true,
}) {
  const { t } = useTranslation(["models", "common"]);
  const { enqueueSnackbar } = useSnackbar();

  const [editedName, setEditedName] = useState(run.name || "");
  const [editedParameters, setEditedParameters] = useState(
    run.parameters || {},
  );
  const [editedOptimizer, setEditedOptimizer] = useState(
    run.optimizer_name || "",
  );
  const [editedOptimizerParams, setEditedOptimizerParams] = useState(
    run.optimizer_parameters || {},
  );
  const [editedGoalMetric, setEditedGoalMetric] = useState(
    run.goal_metric || "",
  );

  const normalizeNestedConfig = useCallback((nested) => {
    if (!nested) return { splitterType: null, nSplits: 2 };

    return {
      splitterType: nested.splitter_name ?? null,
      nSplits: nested.n_splits ?? 2,
    };
  }, []);

  const [editedUseNestedCV, setEditedUseNestedCV] = useState(!!run.nested);
  const [editedInnerConfig, setEditedInnerConfig] = useState(() =>
    normalizeNestedConfig(run.nested),
  );
  const [operationsCount, setOperationsCount] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);

  const { defaultValues: defaultOptimizerParams } = useSchema({
    modelName: enabled ? editedOptimizer : null,
  });
  // The same schema the parameters form fetches, so it shares that request.
  const { defaultValues: defaultModelParams } = useSchema({
    modelName: enabled ? run.model_name : null,
  });

  const runId = run.id;

  const outerSplit = useMemo(() => {
    return session?.splits ? JSON.parse(session.splits) : null;
  }, [session?.splits]);

  useEffect(() => {
    if (!enabled) return;
    setEditedName(run.name || "");
    setEditedParameters(run.parameters || {});
    setEditedOptimizer(run.optimizer_name || "");
    setEditedOptimizerParams(run.optimizer_parameters || {});
    setEditedGoalMetric(run.goal_metric || "");
    setEditedUseNestedCV(!!run.nested);
    setEditedInnerConfig(normalizeNestedConfig(run.nested));
  }, [runId, enabled, run.nested, normalizeNestedConfig]);

  useEffect(() => {
    if (!enabled || !runId) return;
    getRunOperationsCount(runId.toString())
      .then(setOperationsCount)
      .catch((error) =>
        console.error("Error fetching operations count:", error),
      );
  }, [enabled, runId]);

  const hasOptimizableParams = useMemo(
    () => checkIfHaveOptimazers(editedParameters),
    [editedParameters],
  );

  const isDirty = useMemo(() => {
    if (editedName.trim() !== (run.name || "")) return true;
    if (!sameParams(editedParameters, run.parameters || {}, defaultModelParams))
      return true;
    if (editedOptimizer !== (run.optimizer_name || "")) return true;
    if (
      !sameParams(
        editedOptimizerParams,
        run.optimizer_parameters || {},
        defaultOptimizerParams,
      )
    )
      return true;
    if (editedGoalMetric !== (run.goal_metric || "")) return true;
    if (editedUseNestedCV !== !!run.nested) return true;
    if (
      editedUseNestedCV &&
      JSON.stringify(editedInnerConfig) !==
        JSON.stringify(normalizeNestedConfig(run.nested))
    )
      return true;
    return false;
  }, [
    editedName,
    editedParameters,
    defaultModelParams,
    editedOptimizer,
    editedOptimizerParams,
    defaultOptimizerParams,
    editedGoalMetric,
    editedUseNestedCV,
    editedInnerConfig,
    normalizeNestedConfig,
    run,
  ]);

  // While a parameter is marked for optimization, an optimizer and a goal
  // metric are both required — keep Save disabled until they're set instead
  // of letting the user click it and only then learn what's missing.
  const canSave =
    isDirty &&
    (!hasOptimizableParams ||
      (!!editedOptimizer &&
        !!editedGoalMetric &&
        (!editedUseNestedCV ||
          (editedInnerConfig.splitterType && editedInnerConfig.nSplits > 1))));

  const doSave = async () => {
    setSaveConfirmOpen(false);
    setIsSaving(true);

    const optimizing = hasOptimizableParams;

    // If nested CV is enabled, construct the inner splitter configuration to
    // send to the backend. Otherwise, send null to clear any existing nested
    // config.
    let nestedConfig = null;
    if (optimizing && editedUseNestedCV && outerSplit) {
      // Copy the outer splitter configuration and update for inner splitter
      nestedConfig = {
        ...outerSplit,
        splitter_name: editedInnerConfig.splitterType,
        n_splits: editedInnerConfig.nSplits,
      };
    }
    try {
      await updateRunParameters(
        run.id.toString(),
        editedName.trim(),
        editedParameters,
        optimizing ? editedOptimizer || "" : "",
        optimizing
          ? { ...defaultOptimizerParams, ...editedOptimizerParams }
          : {},
        optimizing ? editedGoalMetric || "" : "",
        nestedConfig,
      );

      enqueueSnackbar(
        t("models:message.runUpdatedSuccess", { runName: editedName }),
        { variant: "success" },
      );

      if (onRefresh) await onRefresh();
      if (onSaved) onSaved();
    } catch (error) {
      console.error("Error updating run:", error);
      enqueueSnackbar(
        t("models:error.failedToUpdateRun", {
          error: error.message || t("common:unknownError"),
        }),
        { variant: "error" },
      );
    } finally {
      setIsSaving(false);
    }
  };

  // Shared by the "Next" step transition (only the name needs to be valid to
  // move on to the optimizer step) and the final save (which additionally
  // requires the optimizer/goal metric once there are optimizable params).
  const validateBasics = () => {
    if (!editedName.trim()) {
      enqueueSnackbar(t("models:error.runNameEmpty"), { variant: "warning" });
      return false;
    }

    const nameExists = existingRuns.some(
      (r) =>
        r.id !== run.id &&
        r.name &&
        r.name.toLowerCase() === editedName.trim().toLowerCase(),
    );
    if (nameExists) {
      enqueueSnackbar(
        t("models:error.runNameExists", { name: editedName.trim() }),
        { variant: "error" },
      );
      return false;
    }

    return true;
  };

  const handleSaveEdit = async () => {
    if (!validateBasics()) return;

    if (hasOptimizableParams) {
      if (!editedOptimizer) {
        enqueueSnackbar(t("models:error.selectOptimizerRequired"), {
          variant: "warning",
        });
        return;
      }
      if (!editedGoalMetric) {
        enqueueSnackbar(t("models:error.selectGoalMetricRequired"), {
          variant: "warning",
        });
        return;
      }
    }

    // Re-fetch the count right before confirming — the sidebar stays mounted
    // alongside the Predictions/Explainability tabs, so a value fetched once
    // on mount can go stale if the user creates one there before saving.
    try {
      const currentOperationsCount = await getRunOperationsCount(
        run.id.toString(),
      );
      setOperationsCount(currentOperationsCount);
    } catch (error) {
      console.error("Error fetching operations count:", error);
    }

    // Saving always resets the run to "Not Started" and clears its metrics,
    // even with no existing operations to lose — always confirm first.
    setSaveConfirmOpen(true);
  };

  const handleParametersChange = useCallback((values) => {
    setEditedParameters(values);
  }, []);

  const handleOptimizerParamsChange = useCallback((values) => {
    setEditedOptimizerParams(values);
  }, []);

  const handleOptimizerSelected = (optimizerName) => {
    setEditedOptimizer(optimizerName);
    setEditedOptimizerParams({});
  };

  return {
    editedName,
    setEditedName,
    editedParameters,
    handleParametersChange,
    editedOptimizer,
    editedOptimizerParams,
    setEditedOptimizerParams,
    handleOptimizerParamsChange,
    handleOptimizerSelected,
    editedGoalMetric,
    setEditedGoalMetric,
    hasOptimizableParams,
    isDirty,
    canSave,
    validateBasics,
    operationsCount,
    isSaving,
    saveConfirmOpen,
    setSaveConfirmOpen,
    doSave,
    handleSaveEdit,
    taskName: session?.task_name,
    editedUseNestedCV,
    setEditedUseNestedCV,
    editedInnerConfig,
    setEditedInnerConfig,
  };
}
