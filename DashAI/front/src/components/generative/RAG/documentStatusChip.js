import { DOCUMENT_STATUS } from "../../../hooks/datasets/useDocuments";

/**
 * Explains why a document cannot be picked, as a chip.
 *
 * Shared by the picker and the session attach dialog so both describe the same
 * document state with the same words and colors.
 *
 * @param {object} doc - A Data document.
 * @param {boolean} attached - Whether it is already in the session.
 * @param {Function} t - Translation function.
 * @returns {{label: string, color: string}|null} The chip, or null when the
 *   document can be selected.
 */
export function documentStatusChip(doc, attached, t) {
  if (attached) {
    return {
      label: t("generative:documentPicker.alreadyAttached"),
      color: "success",
    };
  }
  if (doc.status === DOCUMENT_STATUS.ERROR) {
    return { label: t("generative:documentPicker.error"), color: "error" };
  }
  if (doc.status !== DOCUMENT_STATUS.FINISHED) {
    return { label: t("generative:documentPicker.processing"), color: "info" };
  }
  return null;
}
