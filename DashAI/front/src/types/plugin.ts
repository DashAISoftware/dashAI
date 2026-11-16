// Plugin API contract, pinned by test_plugin_contract.py

// A source's trust level, its tier (a shared scale) gives the color
export type TrustLevel = string;
export type TrustTier =
  "attested" | "source" | "unverified" | "local" | "unknown";

export type PluginProblemCode =
  | "damaged"
  | "blocked" // the store retired it as malicious, turning it on asks first
  | "incompatible"
  | "repair_failed"
  | "dependency_unavailable" // a plugin it needs is not active
  | "dependency_version"
  | "load_failed"
  | "restart_required";

export interface PluginError {
  code: string;
  detail: string;
  params: Record<string, unknown>;
}

export interface PluginAuthor {
  name: string;
  email: string;
  url: string;
}

export interface InstalledPlugin {
  id: string;
  name: string;
  version: string;
  components: string[];
  component_types: string[]; // same order as components
  description: string;
  dependencies: string[];
  plugin_dependencies: string[]; // other plugins' ids, as declared
  plugin_specifiers: Record<string, string>;
  authors: PluginAuthor[];
  project_urls: Record<string, string>;
  has_settings: boolean; // its manifest names a settings class
  enabled: boolean; // the user's choice, kept while a problem lasts
  active: boolean; // usable now, what the switch shows
  source: string | null; // "local" or "git", dashAI's PluginSource
  location: string | null; // GitHub repo URL or the uploaded .zip's name
  // From a source that can update (a repo), its page and owner by the back.
  can_update: boolean;
  web_url: string | null;
  owner: string | null;
  ref: string | null; // GitHub tag
  trust_level: TrustLevel;
  trust_tier: TrustTier;
  verified: boolean; // published by DashAISoftware
  sha256: string | null;
  commit: string | null;
  asset: string | null;
  workflow: string | null;
  signed_at: string | null;
  issuer: string | null; // who vouched, from an accepted attestation
  problem: {
    code: PluginProblemCode;
    detail: string;
    params: Record<string, unknown>;
  } | null;
  removed: StoreRemoval | null; // the store retired it (same id and repo)
  // ISO 8601 UTC, the first install of this id and this copy's
  installed_at: string | null;
  updated_at: string | null;
}

export interface PluginPreview {
  is_valid: boolean;
  errors: PluginError[];
  ref: string | null;
  id: string | null;
  version: string | null;
  name: string | null;
  description: string;
  dependencies: string[];
  // The plugins it needs and the ones those need, in install order.
  plugin_dependencies: PluginDependencyInfo[];
  breaks: string[];
  authors: PluginAuthor[];
  project_urls: Record<string, string>;
  readme: string | null;
  installed_version: string | null;
  version_change: "newer" | "same" | "older" | null; // null if not installed
  installed_location: string | null;
  trust_level: TrustLevel | null;
  trust_tier: TrustTier;
  needs_ack: boolean; // tick "I understand the risk" before installing
  verified: boolean;
  sha256: string | null;
  // Installs this very copy without downloading it again, null if invalid.
  preview: string | null;
  removed: StoreRemoval | null; // critical means it installs blocked
  // Decided by the back from source, publisher, store and replaced id
  owner: string | null;
  in_store: boolean;
  replaces_other: boolean;
}

// A needed plugin and what installing does to it
export interface PluginDependencyInfo {
  id: string;
  name: string;
  state: "active" | "disabled" | "store";
  location: string | null;
  ref: string | null;
  latest?: string | null; // its newest tag, if it needs a newer dashAI
}

export type StoreRemoval = "withdrawn" | "unmaintained" | "critical";

// Why reading the store failed. Its last copy is still shown.
export type StoreError =
  "offline" | "rate_limited" | "invalid_store" | "unverified_store";

export interface PluginUpdates {
  checking: boolean;
  // Lookups that blocked or unblocked a plugin, views reload on change
  blocked_changes: number;
  checked_at: string | null;
  updates: Record<string, string>; // plugin id -> newer release's tag
  errors: Record<string, string>; // plugin id -> rate_limited | not_found | offline
  // Store plugin id -> its newest release's tag, which needs a newer dashAI.
  needs_newer_dashai: Record<string, string>;
  store_error: StoreError | null;
}

// The plugin store, its index as the backend last read it.
export interface StoreRelease {
  tag: string;
  version: string;
  min_app_version: string;
  trust_level: TrustLevel; // as the store's review found it
  trust_tier: TrustTier;
  sha256: string; // of the reviewed file, the dialog compares the preview's
  commit: string; // the reviewed commit, where its README is read
  published_at: string;
  dependencies: string[];
  plugin_dependencies: string[]; // other plugins' ids
  plugin_specifiers: Record<string, string>;
  workflow: string | null; // the workflow that built it, if attested
  signed_at: string | null;
}

export interface StoreEntry {
  id: string;
  source: string; // one that can update (dashAI's PluginSource)
  location: string;
  name: string;
  description: string;
  authors: PluginAuthor[];
  components: string[];
  component_types: string[]; // same order as components
  releases: StoreRelease[]; // newest first, at least one
  project_urls: Record<string, string>;
  license: string | null; // the repo's, as an SPDX id
  installed: boolean; // installed here with the same id and repo
  installed_other: boolean; // another plugin with this id is installed
  offered: string | null; // tag of the newest release this dashAI runs
  official: boolean; // from a DashAISoftware repo
  owner: string; // who publishes it, by its source
  web_url: string; // its repo's page
  readme_base: string; // its README's folder at the offered release
  readme_links: string; // where the README's relative links go
}

export interface Store {
  checking: boolean; // being read again, ask again in a moment
  checked_at: string | null; // last successful reading
  error: StoreError | null; // why the last reading failed
  built_at: string | null; // when the store last changed, null if never read
  wrong_versions: Record<string, string[]>;
  plugins: StoreEntry[];
}

// A plugin's settings form, what the form is drawn from and what it shows.
export interface PluginSettings {
  schema: Record<string, unknown>; // a JSON schema, as a component's
  values: Record<string, unknown>; // what is saved, in the form's format
}
