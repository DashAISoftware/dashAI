import { useCallback } from "react";
import { getComponents } from "../api/component";
import { PLUGINS_CHANGED, freshInstalledPlugins } from "../hooks/usePlugins";
import { sharedRead, useSharedRead } from "./sharedRead";

// Whether the components a saved record names (a run's model, a session's
// task and metrics, a chat's model...) are still registered. dashAI's own
// components never leave, so a missing one came from a plugin that was
// disabled, broke or was uninstalled. The record stays visible, only what
// would run the component is blocked.

// What each action on a run makes the backend take from the registry, or
// unpickle, as its job does it (job/model_job.py, predict_job.py,
// explainer_job.py, report_job.py).
const REQUIREMENTS = {
  model: (run) => [run?.model_name],
  optimizer: (run) => [run?.optimizer_name],
  goalMetric: (run) => [run?.goal_metric], // what HPO optimizes
  task: (run, session) => [session?.task_name],
  metrics: (run, session) => [
    ...(session?.train_metrics || []),
    ...(session?.validation_metrics || []),
    ...(session?.test_metrics || []),
  ],
  // Fitted when the session was created and unpickled to train, predict and
  // explain, so their classes must load.
  preprocessing: (run, session) =>
    (session?.preprocessing?.steps || []).map((step) => step.converter),
};

export const NEEDS = {
  train: [
    "model",
    "optimizer",
    "goalMetric",
    "task",
    "metrics",
    "preprocessing",
  ],
  predict: ["model", "task", "preprocessing"],
  explain: ["model", "task", "preprocessing"],
  report: ["model", "task"],
};

export const runNeeds = (action, run, session) =>
  NEEDS[action]
    .flatMap((requirement) => REQUIREMENTS[requirement](run, session))
    .filter(Boolean);

export const sessionComponents = (session) =>
  session ? runNeeds("train", null, session) : [];

// A generative session needs its task and model, plus every component nested
// in its parameters as {component, params}, like a RAG session's generator,
// retriever, prompt... (its model_name is the pipeline itself).
export const generativeSessionComponents = (session) => {
  if (!session) return [];
  const names = [session.task_name, session.model_name];
  const collect = (value) => {
    if (!value || typeof value !== "object") return;
    if (typeof value.component === "string") names.push(value.component);
    Object.values(value).forEach(collect);
  };
  collect(session.parameters);
  return names;
};

// A plugin's component is registered as "<plugin-id>:Class". A record saved
// before ids names it by its class alone, which the backend still resolves
// when a single component has that class (ComponentRegistry.resolve).
const isRegistered = (name, registered) =>
  registered.has(name) ||
  (!name.includes(":") &&
    [...registered].filter((id) => id.split(":").pop() === name).length === 1);

// The names not in `registered`, each with the installed plugin that provides
// it and why it is missing, "disabled", "problem" (enabled but not loaded) or
// "uninstalled" (no installed plugin provides it). Nothing is missing until
// the registry was read once (`registered` null).
export const unavailableComponents = (names, registered, plugins = []) => {
  if (!registered) return [];
  return [...new Set(names.filter(Boolean))]
    .filter((name) => !isRegistered(name, registered))
    .map((name) => {
      const plugin =
        plugins.find((p) =>
          (p.components || []).some((c) => [c, `${p.id}:${c}`].includes(name)),
        ) ?? null;
      const reason = !plugin
        ? "uninstalled"
        : !plugin.enabled
          ? "disabled"
          : "problem";
      return { name, plugin, reason };
    });
};

const unavailableGroups = (missing) => {
  const groups = new Map();
  missing.forEach(({ name, plugin, reason }) => {
    const key = plugin?.id ?? "";
    if (!groups.has(key)) groups.set(key, { plugin, reason, names: [] });
    const { names } = groups.get(key);
    if (!names.includes(name)) names.push(name); // e.g. several runs' metric
  });
  return [...groups.values()];
};

export const unavailableText = (t, missing) =>
  unavailableGroups(missing)
    .map(({ plugin, reason, names }) =>
      t(`plugins:unavailable.${reason}`, {
        names: names.join(", "),
        count: names.length,
        plugin: plugin?.name,
      }),
    )
    .join(" ");

// Shared by every mounted view, the registered names and the installed
// plugins, read once and again after each plugin change (sharing the plugin
// list's read with the plugin views). A failed read keeps the last state (at
// first, nothing is shown as missing).
const availability = sharedRead({
  read: async () => {
    const [components, plugins] = await Promise.all([
      getComponents(),
      freshInstalledPlugins(),
    ]);
    return {
      registered: new Set(components.map((component) => component.name)),
      plugins,
    };
  },
  empty: { registered: null, plugins: [] },
  refreshOn: PLUGINS_CHANGED,
});

// The unavailable ones among `names`, as the API has them now (not as this
// window last saw them), what decides right before something is deleted.
// Shares a read already on its way, so "run all" reads once. Rejects if the
// registry can't be read, so nothing is deleted.
export const checkUnavailable = async (names) => {
  const { registered, plugins } = await availability.fresh();
  return unavailableComponents(names, registered, plugins);
};

// Whether something that deletes results (retraining, saving an edited run)
// may go on, with every name in `names` registered right now. If not, says why
// and returns false, before anything was deleted.
export const confirmAvailable = async (names, t, enqueueSnackbar) => {
  let missing;
  try {
    missing = await checkUnavailable(names);
  } catch {
    enqueueSnackbar(t("plugins:unavailable.checkFailed"), { variant: "error" });
    return false;
  }
  if (missing.length) {
    enqueueSnackbar(unavailableText(t, missing), { variant: "warning" });
    return false;
  }
  return true;
};

export function useComponentAvailability() {
  const { registered, plugins } = useSharedRead(availability).data;
  return useCallback(
    (names) => unavailableComponents(names, registered, plugins),
    [registered, plugins],
  );
}
