import { getApiErrorMessage } from "./apiError";

const KNOWN_CODES = {
  invalid_file: "invalidFile",
  wrong_kind: "wrongKind",
  newer_format: "newerFormat",
  unsafe_file: "unsafeFile",
};

/**
 * Describe a refused session import in the app language.
 *
 * The backend refuses a file with a code and the values its English message
 * was built from, so the reason can be translated here.
 *
 * @param {object} error - The axios error of the import request.
 * @param {Function} t - i18next translator with the "models" namespace.
 * @param {object} [options]
 * @param {object} [options.messageKeys] - Translation keys that replace the
 *   default `models:importError.<name>` for some codes, by code.
 * @param {string} [options.fallbackKey] - Key of the generic failure message.
 * @returns {{message: string, pluginsLink?: string|null}} The message and,
 *   when installing a plugin from the plugins module is the way out, where to
 *   go.
 */
export function describeSessionImportError(error, t, options = {}) {
  const { messageKeys = {}, fallbackKey = "models:error.importSession" } =
    options;
  const detail = error?.response?.data?.detail;
  const code = detail?.code;
  const params = detail?.params || {};

  if (messageKeys[code]) {
    return { message: t(messageKeys[code], params) };
  }
  if (code === "missing_plugin") {
    // published: false means PyPI does not have it (a private plugin the
    // plugins module will never list); null means PyPI could not be asked.
    const isPrivate = params.published === false;
    const unchecked = params.published === null;
    const key = isPrivate
      ? "missingPluginPrivate"
      : unchecked
        ? "missingPluginUnchecked"
        : "missingPlugin";
    let pluginsLink = "/app/plugins/browse";
    if (isPrivate) pluginsLink = null;
    else if (params.plugin_id)
      pluginsLink = `/app/plugins/browse/details/${params.plugin_id}`;
    return {
      message: t(
        `models:importError.${key}${params.version ? "Version" : ""}`,
        params,
      ),
      pluginsLink,
    };
  }
  if (code === "missing_component") {
    return {
      message: t("models:importError.missingComponent", params),
      pluginsLink: "/app/plugins/browse",
    };
  }
  if (KNOWN_CODES[code]) {
    return { message: t(`models:importError.${KNOWN_CODES[code]}`, params) };
  }
  const reason = getApiErrorMessage(error);
  const message = t(fallbackKey);
  return { message: reason ? `${message}: ${reason}` : message };
}
