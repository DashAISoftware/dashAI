/**
 * A session's columns by role, as the backend stores and expects them.
 *
 * The task declares its roles (`metadata.column_roles`) and which of them
 * feed a model's inputs and which its outputs (`metadata.io_roles`); this
 * module only reads those declarations and never names a role itself.
 */
import { keyToRef, rawColumnsNeededFor } from "./sessionColumnRefs";

/** Raw column refs for original column names. */
export const rawRefs = (names = []) =>
  names.map((name) => ({ kind: "raw", name }));

/**
 * The roles a column step shows: every declared role that takes columns.
 * A role whose maximum is 0 says the task takes no such columns. The x/y
 * tasks never declare one (a clustering task declares no target at all), but
 * a task with roles of its own may.
 *
 * @param {object} taskMetadata the task's metadata, with `column_roles`
 * @returns {Array<object>} the roles, in the order the task declares them
 */
export function shownRoles(taskMetadata) {
  return (taskMetadata?.column_roles || []).filter((role) => role.max !== 0);
}

/**
 * The shown roles in the order the column steps display them: the protected
 * roles first, since what the model predicts is the simplest pick and gives
 * the rest their purpose, then the roles the preprocessing may transform.
 * Each group keeps the order the task declares.
 *
 * @param {Array<object>} roles the shown roles
 * @returns {Array<object>} the same roles, protected ones first
 */
export function protectedRolesFirst(roles) {
  return [
    ...roles.filter((role) => !role.transformable),
    ...roles.filter((role) => role.transformable),
  ];
}

/**
 * The selection a column step starts from, over a list of columns.
 *
 * The protected roles take columns from the end, each as many as its
 * minimum (at least one), in the order the task declares them: the last
 * columns of a type the role accepts, when the column types are known, and
 * otherwise the last ones left. The first role the preprocessing may
 * transform takes every other column, in order. For a supervised task, the
 * target is the last column of a target type and the rest are features; for
 * clustering, every column is a feature. Only two declarations are crossed:
 * the types each role accepts and the types of the columns.
 *
 * @param {Array<object>} roles the shown roles
 * @param {string[]} columns the columns to share out
 * @param {Object<string, {type: string}>} [columnTypes] the type of each
 *   column, when known
 * @returns {Object<string, string[]>} role name to its columns
 */
export function defaultRoleSelection(roles, columns, columnTypes = {}) {
  const selection = Object.fromEntries(roles.map((role) => [role.name, []]));
  const left = [...columns];
  const accepts = (role, column) => {
    const type = columnTypes?.[column]?.type;
    return !type || !role.types || role.types.includes(type);
  };
  roles
    .filter((role) => !role.transformable)
    .forEach((role) => {
      const count = Math.min(Math.max(role.min || 0, 1), left.length);
      const taken = [];
      // From the end: the last columns of a type the role accepts...
      for (let i = left.length - 1; i >= 0 && taken.length < count; i -= 1) {
        if (accepts(role, left[i])) taken.unshift(left[i]);
      }
      // ...and, when there are not enough of them, the last ones left.
      for (let i = left.length - 1; i >= 0 && taken.length < count; i -= 1) {
        if (!taken.includes(left[i])) taken.unshift(left[i]);
      }
      selection[role.name] = left.filter((column) => taken.includes(column));
      taken.forEach((column) => left.splice(left.indexOf(column), 1));
    });
  const first = roles.find((role) => role.transformable);
  if (first) {
    selection[first.name] = left;
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
 * @returns {{inputs: string[], inputRefs: Array, rawInputs: string[],
 *   outputs: string[], target: string|undefined}} the input columns
 *   (resolved after the preprocessing), the input refs, the dataset columns
 *   the inputs are computed from (what a hand-typed row has to carry), the
 *   output columns and the first of them
 */
export function sessionColumns(session, taskMetadata) {
  const roles = session?.column_roles || {};
  const sides = taskMetadata?.io_roles || { inputs: [], outputs: [] };
  const gather = (names, key) =>
    names.flatMap((name) => roles[name]?.[key] || []);
  const inputs = gather(sides.inputs, "columns");
  const inputRefs = gather(sides.inputs, "refs");
  const outputs = gather(sides.outputs, "columns");
  const steps = session?.preprocessing?.steps || [];
  return {
    inputs,
    inputRefs,
    // A converter's output (e.g. "bin_SepalLengthCm") is in no dataset: the
    // backend takes the raw values and runs its fitted preprocessor itself.
    // Decided as the backend's session_raw_columns does: by the steps.
    // Without a task declaration nothing is read.
    rawInputs:
      steps.length > 0 && taskMetadata?.io_roles
        ? rawColumnsNeededFor(inputRefs, steps)
        : inputs,
    outputs,
    target: outputs[0],
  };
}

/**
 * A session's columns by role, as the task declares and labels its roles.
 *
 * What a screen lists to say which columns a session uses, without naming
 * them inputs and outputs: a task's roles need not be either (a time index,
 * a series).
 *
 * @param {object} session a model session, with `column_roles`
 * @param {object} taskMetadata the session's task metadata, with
 *   `column_roles`
 * @returns {{name: string, label: string, columns: string[]}[]} the roles
 *   that have columns, in the order the task declares them
 */
export function columnsByRole(session, taskMetadata) {
  const stored = session?.column_roles || {};
  return (taskMetadata?.column_roles || [])
    .map((role) => ({
      name: role.name,
      label: role.label ?? role.name,
      columns: stored[role.name]?.columns || [],
    }))
    .filter((role) => role.columns.length > 0);
}
