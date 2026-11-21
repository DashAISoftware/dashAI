import { useEffect, useState } from "react";
import { getCredentials } from "../../api/credentials";

// Credential authentication is a per-platform fact for the logged-in user (a
// key of theirs is either stored and valid or not). Component lists are fetched once with a
// `credentials_satisfied` snapshot and never refetched, so verifying a
// credential in the dialog would otherwise leave every open list stale until a
// manual page reload. This module-level pub/sub mirrors the download-state
// store: the dialog broadcasts each change and every mounted gate re-derives
// its lock state live, without a scroll-resetting refetch.
const cache = new Map(); // name -> boolean is_authenticated
let loaded = false; // whether the cache has ever been populated
let inFlight = null; // dedupes concurrent initial fetches
let generation = 0; // bumped on every session change, see resetCredentialStatuses
const listeners = new Set(); // (statuses, loaded) => void

const snapshot = () => Object.fromEntries(cache);

const notify = () => {
  const snap = snapshot();
  listeners.forEach((listener) => listener(snap, loaded));
};

// Update a single credential's status and broadcast. Called by the credentials
// dialog after a successful verify/delete so lists react immediately.
export const setCredentialStatus = (name, isAuthenticated) => {
  cache.set(name, Boolean(isAuthenticated));
  loaded = true;
  notify();
};

// Seed the whole cache from a getCredentials() payload and broadcast.
export const setCredentialStatuses = (credentials) => {
  (credentials || []).forEach((cred) =>
    cache.set(cred.name, Boolean(cred.is_authenticated)),
  );
  loaded = true;
  notify();
};

// Forget the statuses when the session changes: credentials belong to each
// user, so the next user's must be fetched again. Nothing is fetched here
// (right after a logout it would answer 401): the views remount with the new
// session and fetch on their own, because `loaded` is false. A fetch still in
// flight belongs to the previous user, so its answer is dropped.
export const resetCredentialStatuses = () => {
  generation += 1;
  inFlight = null;
  cache.clear();
  loaded = false;
  notify();
};

// Fetch the current statuses once and populate the cache. Concurrent callers
// share the same in-flight request so a screen with many gates fetches once.
export const refreshCredentialStatuses = () => {
  if (inFlight) return inFlight;
  const requestGeneration = generation;
  // Wrap in Promise.resolve so a synchronous/non-promise return (e.g. a mocked
  // getCredentials in tests) can never throw on `.then`.
  const request = Promise.resolve(getCredentials())
    .then((data) => {
      if (requestGeneration === generation) setCredentialStatuses(data);
    })
    .catch(() => {})
    .finally(() => {
      if (inFlight === request) inFlight = null;
    });
  inFlight = request;
  return request;
};

// Subscribe to the live credential statuses. Triggers the initial fetch on
// first mount and returns { statuses, loaded }. `statuses` is a plain
// name -> boolean object; `loaded` is false until the first fetch resolves.
export const useCredentialStatuses = () => {
  const [state, setState] = useState(() => ({
    statuses: snapshot(),
    loaded,
  }));

  useEffect(() => {
    const listener = (statuses, isLoaded) =>
      setState({ statuses, loaded: isLoaded });
    listeners.add(listener);
    // Reconcile anything that changed between first render and subscribe.
    setState({ statuses: snapshot(), loaded });
    if (!loaded) refreshCredentialStatuses();
    return () => {
      listeners.delete(listener);
    };
  }, []);

  return state;
};

// Derive a human label from a credential component name, e.g.
// "HuggingFaceCredential" -> "HuggingFace". Falls back to the raw name so it
// works for any backend registered credential without frontend changes.
export const credentialLabel = (name) =>
  name.replace(/Credential$/, "") || name;

// Compute a component's credential gating from the live statuses. Falls back to
// the component's server provided `credentials_satisfied` flag until the live
// cache has loaded, so the gate is correct on first paint.
export const getComponentCredentialState = (component, statuses, isLoaded) => {
  const requiredCredentials = component?.required_credentials ?? [];
  const optionalCredentials = component?.optional_credentials ?? [];
  const credentialsSatisfied = isLoaded
    ? requiredCredentials.every((cred) => statuses[cred] === true)
    : component?.credentials_satisfied !== false;
  // Unmet required credentials make the component unusable.
  const locked = !credentialsSatisfied && requiredCredentials.length > 0;
  return {
    requiredCredentials,
    optionalCredentials,
    credentialsSatisfied,
    locked,
    requiredPlatforms: requiredCredentials.map(credentialLabel).join(", "),
    optionalPlatforms: optionalCredentials.map(credentialLabel).join(", "),
  };
};
