/**
 * A session's columns by role, as the backend stores and expects them.
 *
 * The task declares its roles and which of them feed a model's inputs and
 * which its outputs (`metadata.io_roles`); this module only reads that
 * declaration and never names a role itself.
 */

/** Raw column refs for original column names. */
export const rawRefs = (names = []) =>
  names.map((name) => ({ kind: "raw", name }));

/**
 * The session's roles built from the model's inputs and outputs, the way the
 * column step still keeps them: the inputs go to the task's input role and
 * the outputs to its output role. Roles given nothing are left out.
 *
 * Only tasks with one role per side can be built this way, which is every
 * task whose column step keeps inputs and outputs.
 *
 * @param {object} taskMetadata the task's metadata, with `io_roles`
 * @param {Array} inputs the model's inputs (column refs, or names)
 * @param {Array} outputs the model's outputs (column refs, or names)
 * @returns {Object<string, Array>} role name to the role's columns
 */
export function rolesFromIo(taskMetadata, inputs = [], outputs = []) {
  const sides = taskMetadata?.io_roles || { inputs: [], outputs: [] };
  const roles = {};
  if (sides.inputs.length === 1 && inputs.length > 0) {
    roles[sides.inputs[0]] = inputs;
  }
  if (sides.outputs.length === 1 && outputs.length > 0) {
    roles[sides.outputs[0]] = outputs;
  }
  return roles;
}
