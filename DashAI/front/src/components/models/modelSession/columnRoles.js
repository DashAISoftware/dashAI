/**
 * A session's columns by role, as the backend stores and expects them.
 *
 * The task declares its roles (`metadata.column_roles`) and which of them
 * feed a model's inputs and which its outputs (`metadata.io_roles`); this
 * module only reads those declarations and never names a role itself.
 */
import { keyToRef } from "./sessionColumnRefs";

/** Raw column refs for original column names. */
export const rawRefs = (names = []) =>
  names.map((name) => ({ kind: "raw", name }));

/**
 * The roles a column step shows: every declared role that takes columns.
 * A role whose maximum is 0 says the task takes no such columns (e.g. the
 * target of a clustering task).
 *
 * @param {object} taskMetadata the task's metadata, with `column_roles`
 * @returns {Array<object>} the roles, in the order the task declares them
 */
export function shownRoles(taskMetadata) {
  return (taskMetadata?.column_roles || []).filter((role) => role.max !== 0);
}

/**
 * The selection a column step starts from, over a list of columns.
 *
 * The protected roles take columns from the end, each as many as its
 * minimum (at least one), in the order the task declares them; the first
 * role the preprocessing may transform takes every other column. For a
 * supervised task, the last column is the target and the rest are features;
 * for clustering, every column is a feature.
 *
 * @param {Array<object>} roles the shown roles
 * @param {string[]} columns the columns to share out
 * @returns {Object<string, string[]>} role name to its columns
 */
export function defaultRoleSelection(roles, columns) {
  const selection = Object.fromEntries(roles.map((role) => [role.name, []]));
  let end = columns.length;
  roles
    .filter((role) => !role.transformable)
    .forEach((role) => {
      const count = Math.min(Math.max(role.min || 0, 1), end);
      selection[role.name] = columns.slice(end - count, end);
      end -= count;
    });
  const first = roles.find((role) => role.transformable);
  if (first) {
    selection[first.name] = columns.slice(0, end);
  }
  return selection;
}

/**
 * Whether a selection is complete enough to be checked by the backend:
 * every required role has columns, and the roles the preprocessing may
 * transform have at least one between them.
 *
 * @param {Array<object>} roles the shown roles
 * @param {Object<string, string[]>} selection role name to its columns
 * @returns {boolean}
 */
export function selectionReady(roles, selection) {
  const has = (role) => (selection[role.name] || []).length > 0;
  const transformable = roles.filter((role) => role.transformable);
  return (
    roles.every((role) => !role.required || has(role)) &&
    (transformable.length === 0 || transformable.some(has))
  );
}

/**
 * The options a role can pick from.
 *
 * A protected role sees every option but those other protected roles hold:
 * picking a feature as the target moves it there (see resolveSelection). A
 * role the preprocessing may transform does not see what any other role
 * holds.
 *
 * @param {object} role the role
 * @param {string[]} options every option of the step
 * @param {Object<string, string[]>} selection role name to its columns
 * @param {Array<object>} roles the shown roles
 * @returns {string[]}
 */
export function optionsForRole(role, options, selection, roles) {
  const protectedNames = new Set(
    roles.filter((other) => !other.transformable).map((other) => other.name),
  );
  const takenElsewhere = new Set(
    Object.entries(selection)
      .filter(
        ([name]) =>
          name !== role.name &&
          (role.transformable || protectedNames.has(name)),
      )
      .flatMap(([, columns]) => columns),
  );
  return options.filter((option) => !takenElsewhere.has(option));
}

/**
 * A selection where every column plays one role at most.
 *
 * When two roles hold the same column, the protected role keeps it (a column
 * picked as the target stops being a feature), then the roles in the order
 * the task declares them. Roles not shown are dropped.
 *
 * @param {Array<object>} roles the shown roles
 * @param {Object<string, string[]>} selection role name to its columns
 * @returns {Object<string, string[]>}
 */
export function resolveSelection(roles, selection) {
  const ordered = [
    ...roles.filter((role) => !role.transformable),
    ...roles.filter((role) => role.transformable),
  ];
  const claimed = new Set();
  const resolved = {};
  ordered.forEach((role) => {
    resolved[role.name] = (selection[role.name] || []).filter((column) => {
      if (claimed.has(column)) return false;
      claimed.add(column);
      return true;
    });
  });
  return Object.fromEntries(
    roles.map((role) => [role.name, resolved[role.name]]),
  );
}

/**
 * A selection of option keys turned into the column refs the API takes.
 * Roles given nothing are left out.
 *
 * @param {Object<string, string[]>} selection role name to option keys
 * @returns {Object<string, Array>} role name to column refs
 */
export function selectionToRefs(selection) {
  return Object.fromEntries(
    Object.entries(selection)
      .filter(([, keys]) => keys.length > 0)
      .map(([name, keys]) => [name, keys.map(keyToRef)]),
  );
}

/**
 * A session's columns as the model's inputs and outputs.
 *
 * Read from the roles the session stores, through the roles the task says
 * feed each side (`metadata.io_roles`).
 *
 * @param {object} session a model session, with `column_roles`
 * @param {object} taskMetadata the session's task metadata, with `io_roles`
 * @returns {{inputs: string[], inputRefs: Array, outputs: string[],
 *   target: string|undefined}} the input columns (resolved after the
 *   preprocessing), the input refs, the output columns and the first of them
 */
export function sessionColumns(session, taskMetadata) {
  const roles = session?.column_roles || {};
  const sides = taskMetadata?.io_roles || { inputs: [], outputs: [] };
  const gather = (names, key) =>
    names.flatMap((name) => roles[name]?.[key] || []);
  const outputs = gather(sides.outputs, "columns");
  return {
    inputs: gather(sides.inputs, "columns"),
    inputRefs: gather(sides.inputs, "refs"),
    outputs,
    target: outputs[0],
  };
}
