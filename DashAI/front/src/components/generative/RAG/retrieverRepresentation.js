import { resolveLocalizedText } from "../../../utils/localize";
import {
  MISSING_VALUE,
  normalizeComponentRef,
  resolveParamValue,
} from "./paramResolution";

// Re-export the generic resolution helpers for backward compatibility.
export { MISSING_VALUE, normalizeComponentRef, resolveParamValue };

/**
 * Build the lookup that turns a component class name into its localized
 * `display_name`, as declared by the component itself.
 *
 * @param {function(string): (object|null|undefined)} [resolveComponent] -
 *   Lookup for component definitions by class name.
 * @param {object|string} i18n - i18next instance or language code.
 * @returns {function(string): (string|null)|undefined} The renderer, or
 *   undefined when no component lookup is available. It returns null for
 *   unknown components or components without a display name.
 */
export function buildComponentNameRenderer(resolveComponent, i18n) {
  if (typeof resolveComponent !== "function") return undefined;
  return (componentName) => {
    try {
      return resolveLocalizedText(
        resolveComponent(componentName)?.display_name,
        i18n,
      );
    } catch {
      return null;
    }
  };
}

/**
 * Substitute every `{...}` placeholder in a representation template.
 *
 * @param {string} template - Representation template.
 * @param {*} params - Node parameters used to resolve placeholders.
 * @param {function(string): (string|null|undefined)} [renderComponentName] -
 *   Optional lookup returning the localized display name of a component class
 *   name, used for placeholders that resolve to a component reference.
 * @returns {string|null} The interpolated text, or null when the template is
 *   missing, interpolation fails unexpectedly, or no placeholder resolves
 *   (so an all-em-dash caption never hides the component description).
 */
export function interpolateRepresentation(
  template,
  params,
  renderComponentName,
) {
  if (typeof template !== "string" || template.length === 0) return null;

  try {
    let sawPlaceholder = false;
    let resolvedPlaceholder = false;
    const rendered = template.replace(/\{([^{}]+)\}/g, (_match, token) => {
      sawPlaceholder = true;
      const path = token.trim().split(".").filter(Boolean);
      const value =
        path.length > 0
          ? resolveParamValue(params, path, renderComponentName)
          : MISSING_VALUE;
      if (value !== MISSING_VALUE) resolvedPlaceholder = true;
      return value;
    });

    return !sawPlaceholder || resolvedPlaceholder ? rendered : null;
  } catch {
    return null;
  }
}

/**
 * Resolve a retriever's declarative representation against its current params.
 * The template lives in `component.metadata.representation` and may be a plain
 * string or a multilingual object.
 *
 * @param {object|null|undefined} component - Retriever component definition.
 * @param {*} params - Current parameters of the retriever node.
 * @param {object|string} i18n - i18next instance or language code.
 * @param {function(string): (object|null|undefined)} [resolveComponent] -
 *   Lookup for component definitions by class name. When given, component
 *   references in the template render their localized `display_name`.
 * @returns {string|null} The rendered representation, or null when the
 *   component has no template or none of its placeholders resolves.
 */
export function resolveRetrieverRepresentation(
  component,
  params,
  i18n,
  resolveComponent,
) {
  try {
    const template = resolveLocalizedText(
      component?.metadata?.representation,
      i18n,
    );
    if (!template) return null;
    return interpolateRepresentation(
      template,
      params,
      buildComponentNameRenderer(resolveComponent, i18n),
    );
  } catch {
    return null;
  }
}
