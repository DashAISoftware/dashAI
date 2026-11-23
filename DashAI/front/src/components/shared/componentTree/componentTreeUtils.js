/**
 * Pure helpers of the generic component tree.
 *
 * A tree node is a component with its params. A node is a *container* when its
 * schema declares a list of components: an array property whose `items` carry a
 * `parent` class (what `list_field(component_field(parent=...))` serialises to).
 * That declaration is the only source of truth, so the tree never names a
 * container class, a children key or a child parent: any component with such a
 * field becomes a container and any registry parent can be the tree's root.
 */

import { SCHEMA_TYPE_ARRAY } from "../../../constants/rag";

/**
 * A node of the editable tree.
 *
 * @typedef {object} TreeNode
 * @property {string} nodeId - Unique id within the tree.
 * @property {string} component - Registered component name, empty while a new
 *   child has not been configured yet.
 * @property {object} params - The component params, without its children.
 * @property {TreeNode[]} children - The configured children, empty for a
 *   component that is not a container.
 */

/**
 * The list-of-components property of a component schema.
 *
 * @typedef {object} ChildrenField
 * @property {string} key - The property key.
 * @property {string} parent - The parent class its items must inherit.
 * @property {number} minItems - Minimum number of children.
 * @property {(number|null)} maxItems - Maximum number of children, if any.
 */

/**
 * Whether a value is a non-null, non-array object.
 * @param {*} value - Value to test.
 * @returns {boolean} True for a plain object.
 */
export function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

/**
 * Finds the list-of-components property of a component schema.
 *
 * Optional arrays arrive wrapped in an `anyOf`, so that shape is read too.
 *
 * @param {object|undefined} schema - A component's JSON schema.
 * @returns {ChildrenField|null} The property key, the parent class its items
 *   must inherit and its size limits, or null when the component is not a
 *   container.
 */
export function findChildrenField(schema) {
  const properties = schema?.properties;
  if (!isPlainObject(properties)) return null;
  for (const [key, property] of Object.entries(properties)) {
    const array =
      property?.type === SCHEMA_TYPE_ARRAY
        ? property
        : property?.anyOf?.find((branch) => branch?.type === SCHEMA_TYPE_ARRAY);
    const parent = array?.items?.parent;
    if (parent) {
      return {
        key,
        parent,
        minItems: array.minItems ?? 0,
        maxItems: array.maxItems ?? null,
      };
    }
  }
  return null;
}

/**
 * Creates a node id generator, so each tree numbers its own nodes.
 * @returns {function(): string} A function returning a new unique id per call.
 */
export function createIdFactory() {
  let counter = 0;
  return () => `n_${++counter}`;
}

/**
 * Returns the child refs of a serialised ref.
 *
 * A top-level array under the children key is authoritative whenever it exists,
 * even when empty: canonical refs never carry it, so its presence identifies
 * the legacy shape that stored children next to `params`. Otherwise the
 * canonical `params[key]` is used.
 *
 * @param {object} ref - Serialised `{component, params}` ref.
 * @param {string} key - The children property key of the ref's component.
 * @returns {object[]} The child refs, or an empty array.
 */
export function getChildRefs(ref, key) {
  if (Array.isArray(ref?.[key])) return ref[key];
  if (Array.isArray(ref?.params?.[key])) return ref.params[key];
  return [];
}

/**
 * Recursively maps a serialised ref into an editable tree node.
 *
 * Refs that are malformed or name an unknown component are dropped (null), so
 * unknown components never enter the tree. A ref without `params` is the
 * minimal ref `{component}`: its params are the component's defaults, which the
 * form resolves when the node is edited.
 *
 * @param {object} ref - Serialised ref to map.
 * @param {function(string): (object|null)} findComponent - Component lookup.
 * @param {function(): string} nextId - Node id generator.
 * @returns {TreeNode|null} The tree node, or null.
 */
export function buildNodeFromRef(ref, findComponent, nextId) {
  if (!isPlainObject(ref)) return null;
  const info = findComponent(ref.component);
  if (!info) return null;
  const field = findChildrenField(info.schema);
  return {
    nodeId: nextId(),
    component: ref.component,
    params: ref.params || {},
    children: field
      ? getChildRefs(ref, field.key)
          .map((child) => buildNodeFromRef(child, findComponent, nextId))
          .filter(Boolean)
      : [],
  };
}

/**
 * Serialises a node back to the canonical `{component, params}` ref, with the
 * children of containers under their own property key.
 *
 * @param {TreeNode} node - Tree node.
 * @param {function(string): (object|null)} findComponent - Component lookup.
 * @returns {{component: string, params: object}} The canonical ref.
 */
export function serializeNode(node, findComponent) {
  const field = findChildrenField(findComponent(node.component)?.schema);
  const params = { ...node.params };
  if (field) {
    params[field.key] = node.children
      .map((child) => serializeNode(child, findComponent))
      .filter((child) => child.component);
  }
  return { component: node.component, params };
}

/**
 * Immutably updates the node identified by `nodeId`.
 * @param {object} root - Tree root.
 * @param {string} nodeId - Target node id.
 * @param {function(object): object} fn - Receives the node, returns its update.
 * @returns {object} A new tree.
 */
export function updateAt(root, nodeId, fn) {
  const walk = (node) => {
    if (node.nodeId === nodeId) return fn(node);
    return { ...node, children: node.children.map(walk) };
  };
  return walk(root);
}

/**
 * Finds a node by id.
 * @param {object} tree - Tree root.
 * @param {string} nodeId - Node id.
 * @returns {object|null} The node, or null.
 */
export function findNode(tree, nodeId) {
  if (tree.nodeId === nodeId) return tree;
  for (const child of tree.children) {
    const found = findNode(child, nodeId);
    if (found) return found;
  }
  return null;
}

/**
 * Finds the parent of a node.
 * @param {object} tree - Tree root.
 * @param {string} nodeId - Child node id.
 * @returns {object|null} The parent node, or null for the root or unknown ids.
 */
export function findParentNode(tree, nodeId) {
  for (const child of tree.children) {
    if (child.nodeId === nodeId) return tree;
    const found = findParentNode(child, nodeId);
    if (found) return found;
  }
  return null;
}

/**
 * The category a component is grouped under.
 * @param {object} component - A component from the registry.
 * @param {string} fallback - Label used when it declares none.
 * @returns {string} The category.
 */
export function componentCategory(component, fallback) {
  return component?.metadata?.category || fallback;
}

/**
 * Orders components so each category is contiguous, keeping the categories in
 * the order they first appear, as grouped autocompletes require.
 * @param {object[]} components - Components to order.
 * @param {string} fallback - Category for components that declare none.
 * @returns {object[]} A new, grouped array.
 */
export function sortByCategory(components, fallback) {
  const order = [];
  for (const component of components) {
    const category = componentCategory(component, fallback);
    if (!order.includes(category)) order.push(category);
  }
  return [...components].sort(
    (a, b) =>
      order.indexOf(componentCategory(a, fallback)) -
      order.indexOf(componentCategory(b, fallback)),
  );
}

/**
 * Keeps the components a user can configure, once each, grouped by category.
 * @param {object[]} components - Candidate components.
 * @param {string} fallback - Category for components that declare none.
 * @returns {object[]} The selectable options.
 */
export function selectableOptions(components, fallback) {
  const seen = new Set();
  return sortByCategory(
    components
      .filter((component) => component.configurable_object !== false)
      .filter((component) => {
        if (seen.has(component.name)) return false;
        seen.add(component.name);
        return true;
      }),
    fallback,
  );
}
