import {
  findChildrenField,
  getChildRefs,
} from "../../shared/componentTree/componentTreeUtils";

/**
 * Whether a serialised component tree is complete enough to be saved.
 *
 * A node that declares a list of children (a container such as a sequential or
 * MMR reranker retriever) needs at least one configured child, or as many as
 * its own `minItems` asks for, and every child must be complete in turn. A
 * node that is not a container is always complete. Unknown components and
 * children without a component are treated as incomplete, since the backend
 * would reject them.
 *
 * @param {{component: string, params: object}|null|undefined} ref - The
 *   serialised `{component, params}` tree root.
 * @param {function(string): (object|null)} findComponent - Looks a component
 *   up by name; it must return the component object, whose `schema` is read.
 * @returns {boolean} True when every container in the tree has its children.
 */
export function isCompositeTreeComplete(ref, findComponent) {
  if (!ref?.component) return false;
  const info = findComponent(ref.component);
  if (!info) return false;
  const childrenField = findChildrenField(info.schema);
  if (!childrenField) return true;
  const children = getChildRefs(ref, childrenField.key);
  if (children.length < Math.max(1, childrenField.minItems)) return false;
  return children.every((child) =>
    isCompositeTreeComplete(child, findComponent),
  );
}
