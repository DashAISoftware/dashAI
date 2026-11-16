import TaskAltIcon from "@mui/icons-material/TaskAlt";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import GitHubIcon from "@mui/icons-material/GitHub";
import PublicIcon from "@mui/icons-material/Public";

// One color per TrustTier (back/plugins/sources/base.py), best first
const TRUST = {
  attested: { Icon: TaskAltIcon, color: "#43A047" },
  source: { Icon: CheckCircleOutlineIcon, color: "#F9A825" },
  unverified: { Icon: WarningAmberIcon, color: "#EF6C00" },
  local: { Icon: ErrorOutlineIcon, color: "#D32F2F" },
  unknown: { Icon: HelpOutlineIcon, color: "#9E9E9E" },
};

export const trustOf = (tier) => TRUST[tier] ?? TRUST.unknown;

export const trustText = (trust, field) => [
  `plugins:trust.${trust.trust_level ?? "unknown"}.${field}`,
  `plugins:tier.${trust.trust_tier ?? "unknown"}.${field}`,
];

// Keep it off until fixed or reopened, enabling retries a load_failed one
const BLOCKS_TOGGLE = new Set([
  "damaged",
  "dependency_version",
  "incompatible",
  "repair_failed",
  "restart_required",
]);
const FIXED_BY_REINSTALL = new Set(["damaged", "repair_failed"]);

// The active plugins needing ``id`` directly or not, nearest first
export const dependentsOf = (plugins, id) => {
  const found = [];
  for (let i = -1; i < found.length; i += 1) {
    const needed = i < 0 ? id : found[i].id;
    plugins.forEach((plugin) => {
      if (
        plugin.active &&
        plugin.id !== id &&
        !found.includes(plugin) &&
        (plugin.plugin_dependencies || []).includes(needed)
      ) {
        found.push(plugin);
      }
    });
  }
  return found;
};

// Needs keeping it off as {id, name, reason}, in the order to enable them
export const unmetDependencies = (
  plugin,
  plugins,
  seen = new Set([plugin.id]),
) =>
  (plugin.plugin_dependencies || []).flatMap((id) => {
    if (seen.has(id)) return [];
    seen.add(id);
    const needed = plugins.find((p) => p.id === id);
    if (!needed) return [{ id, name: id, reason: "uninstalled" }];
    if (needed.active) return [];
    const behind = unmetDependencies(needed, plugins, seen);
    const code = needed.problem?.code;
    if (needed.enabled && code === "dependency_unavailable") return behind;
    const reason = code || needed.enabled ? "problem" : "disabled";
    return [...behind, { id, name: needed.name, reason }];
  });

export const canToggle = (plugin, plugins = []) =>
  (!plugin.problem || !BLOCKS_TOGGLE.has(plugin.problem.code)) &&
  (plugin.active ||
    unmetDependencies(plugin, plugins).every(
      ({ reason }) => reason === "disabled",
    ));
export const canReinstall = (plugin, newVersion = null) =>
  !newVersion &&
  !!plugin.problem &&
  FIXED_BY_REINSTALL.has(plugin.problem.code);

export const fileName = (path) =>
  (path || "").split(/[\\/]/).filter(Boolean).pop() || path;

export const shortUrl = (url) =>
  (url || "").replace(/^https?:\/\//, "").replace(/\/$/, "");

export const SOURCES = {
  git: {
    name: "GitHub",
    Icon: GitHubIcon,
    tooltip: "plugins:label.fromGithub",
    pages: { github: "", issues: "/issues" },
  },
};

const hostOf = (url) => {
  try {
    return new URL(url).host;
  } catch {
    return null;
  }
};

export const sourceOf = (plugin) =>
  SOURCES[plugin.source] ?? { name: hostOf(plugin.web_url), Icon: PublicIcon };

export const pluginLinks = (plugin) => {
  const { name, pages } = sourceOf(plugin);
  const base = plugin.can_update && plugin.web_url;
  const links = !base
    ? []
    : pages
      ? Object.entries(pages).map(([key, path]) => ({ key, url: base + path }))
      : [{ label: name, url: base }];
  const seen = new Set(links.map(({ url }) => url.toLowerCase()));
  Object.entries(plugin.project_urls || {}).forEach(([label, url]) => {
    const same = url.replace(/\/+$/, "").toLowerCase();
    if (!seen.has(same)) links.push({ label, url });
    seen.add(same);
  });
  return links;
};

// First author's name, link or email, else its owner, +n for more authors
export const authorLine = (plugin) => {
  const [first, ...rest] = plugin.authors || [];
  const who =
    first?.name || shortUrl(first?.url) || first?.email || plugin.owner;
  if (!who) return null;
  return rest.length ? `${who} +${rest.length}` : who;
};

export const componentTypes = (plugin) => [
  ...new Set(plugin.component_types || []),
];

// Explorar lists only the store, so it has no status to filter by
export const STATUS_FILTERS = {
  explore: [],
  installed: ["all", "enabled", "disabled", "warnings", "updates"],
};
export const NO_FILTERS = { search: "", tag: "", status: "all", origin: "all" };

export const PAGE_SIZES = [9, 12, 24, 48];
// In localStorage so it survives a restart
export const savedPageSize = () => {
  const saved = Number(localStorage.getItem("plugins.pageSize"));
  return PAGE_SIZES.includes(saved) ? saved : PAGE_SIZES[0];
};

export const matchesStatus = (plugin, status, updates) => {
  if (status === "enabled") return plugin.active;
  if (status === "disabled") return !plugin.active;
  if (status === "warnings") return !!plugin.problem || !!plugin.removed;
  if (status === "updates") return !!updates[plugin.id];
  return true;
};

const originOf = (plugin) => plugin.source || "local";

export const originFilters = (plugins, selected) => [
  "all",
  ...[...new Set([...plugins.map(originOf), selected])]
    .filter((origin) => origin !== "all")
    .sort(),
];

export const matchesOrigin = (plugin, origin) =>
  origin === "all" || originOf(plugin) === origin;

const matchesSearch = (plugin, search) => {
  const text = search.trim().toLowerCase();
  if (!text) return true;
  return [plugin.name, plugin.id, plugin.description, ...plugin.components]
    .filter(Boolean)
    .some((value) => value.toLowerCase().includes(text));
};

export const filterPlugins = (plugins, filters, updates = {}) =>
  plugins.filter(
    (plugin) =>
      matchesSearch(plugin, filters.search) &&
      (!filters.tag || plugin.component_types.includes(filters.tag)) &&
      matchesStatus(plugin, filters.status, updates) &&
      matchesOrigin(plugin, filters.origin),
  );

const time = (value) => (value ? new Date(value).getTime() : 0);

export const sortPlugins = (plugins, sortBy) => {
  const sorted = [...plugins];
  if (sortBy === "name") {
    return sorted.sort((a, b) => a.name.localeCompare(b.name));
  }
  const newest = (a, b) => time(b.updated_at) - time(a.updated_at);
  return sorted.sort(sortBy === "oldest" ? (a, b) => -newest(a, b) : newest);
};

// The message for a coded error, the technical detail if unknown
export const errorMessage = (t, error) => {
  const params = {};
  Object.entries(error.params || {}).forEach(([key, value]) => {
    const names =
      Array.isArray(value) && value.every((v) => typeof v === "string");
    params[key] = names ? value.join(", ") : value;
  });
  if (params.owner === "dashai") params.owner = "dashAI";
  let key = `plugins:errors.${error.code}`;
  if (error.code === "rate_limited") {
    if (params.resets_at) {
      params.time = new Date(params.resets_at * 1000).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
    } else {
      key = "plugins:errors.rate_limited_later";
    }
  }
  if (error.code === "dependency_unavailable") {
    params.name ??= params.id;
    if (params.problem) {
      params.problem = t(`plugins:problem.${params.problem}.title`);
    } else {
      key = "plugins:errors.dependency_inactive";
    }
  }
  if (
    error.code === "missing_plugin_dependency" &&
    params.store_read === false
  ) {
    key = "plugins:errors.missing_plugin_dependency_unread";
  }
  if (error.code === "plugin_dependency_version" && params.installed == null) {
    key = "plugins:errors.plugin_dependency_version_store";
  }
  if (error.code === "dependency_cycle") params.ids = error.params.ids;
  return t(key, { ...params, defaultValue: error.detail });
};

export const errorList = (error) =>
  error.code === "invalid_plugin" && Array.isArray(error.params?.errors)
    ? error.params.errors
    : [error];

export const formatDate = (value, language) =>
  value
    ? new Date(value).toLocaleString(language, {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

// The message after Check for updates, as [variant, key, params]
export const updatesMessage = ({
  updates,
  errors = {},
  store_error: storeError = null,
}) => {
  const found = Object.keys(updates).length;
  if (found) return ["info", "updatesFound", { count: found }];
  const failed = Object.values(errors);
  if (!failed.length && !storeError) return ["info", "noUpdates", {}];
  if ([...failed, storeError].every((code) => !code || code === "offline")) {
    return ["warning", "checkOffline", {}];
  }
  return storeError
    ? ["warning", "storeCheckFailed", {}]
    : ["warning", "checkFailed", { count: failed.length }];
};

export const asVersion = (value) =>
  value ? `v${String(value).replace(/^v/, "")}` : null;

// Whether updating installs a newer copy, null if nothing to compare
export const canUpdateTo = (preview, installedRef) =>
  preview.version_change === "newer" ||
  preview.version_change === null ||
  (preview.version_change === "same" && preview.ref !== installedRef);

export const versionNotice = (preview, updating) => {
  if (preview.version_change === "older") {
    return updating ? "olderUpdate" : "older";
  }
  if (preview.version_change === "same" && updating) return "sameRelease";
  return null;
};

const offeredRelease = (entry) =>
  entry.releases.find(({ tag }) => tag === entry.offered) ?? entry.releases[0];

export const storePlugin = (entry) => {
  const release = offeredRelease(entry);
  return {
    ...entry,
    fromStore: true,
    can_update: true, // the store lists only what a source can update
    version: release.version,
    ref: release.tag,
    sha256: release.sha256,
    commit: release.commit,
    workflow: release.workflow,
    signed_at: release.signed_at,
    published_at: release.published_at,
    dependencies: release.dependencies,
    plugin_dependencies: release.plugin_dependencies,
    plugin_specifiers: release.plugin_specifiers,
    trust_level: release.trust_level,
    trust_tier: release.trust_tier,
    updated_at: entry.releases[0].published_at, // "newest" is its last release
    verified: entry.official,
    active: true,
    problem: null,
  };
};

// A README url resolved against base, only http(s), else null
export const resolveReadmeUrl = (url, base) => {
  if (!url || url.startsWith("#")) return url || null;
  try {
    const resolved = new URL(url, base ?? undefined);
    return ["http:", "https:", "mailto:"].includes(resolved.protocol)
      ? resolved.href
      : null;
  } catch {
    return null; // relative, without a base to resolve it against
  }
};

export const splitRequirement = (requirement) => {
  const match = /^([A-Za-z0-9_.\-[\],]+)\s*(.*)$/.exec(requirement);
  return match ? [match[1], match[2]] : [requirement, ""];
};
