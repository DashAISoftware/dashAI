import { useCallback, useMemo, useState } from "react";
import { DOCUMENT_STATUS } from "../../../hooks/datasets/useDocuments";

/** Key of the group that holds documents outside any known folder. */
const LOOSE_GROUP_KEY = "loose";

/** Shared empty set so a caller without attachments does not break memoization. */
const NO_ATTACHED_IDS = new Set();

/**
 * Compares two named rows using natural, case-insensitive ordering.
 *
 * @param {{name: string}} left - First row.
 * @param {{name: string}} right - Second row.
 * @returns {number} The comparison result.
 */
function compareByName(left, right) {
  return left.name.localeCompare(right.name, undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

/**
 * Manages a multi-folder, multi-document selection over the Data library.
 *
 * A single set of document ids is the source of truth: a folder's checked and
 * indeterminate states are derived from the ids it currently has, so a folder
 * never stores its own selection and stale library rows cannot keep selecting
 * documents that no longer exist.
 *
 * `groups` has one entry per folder that currently holds documents (empty
 * folders are omitted) plus one loose group when documents have no known
 * folder. Each entry is `{ key, folder, documents, selectableIds, checked,
 * indeterminate, disabled }`, where `folder` is null for the loose group,
 * `selectableIds` are the ids that can be attached, and `checked`/
 * `indeterminate`/`disabled` describe that folder's checkbox.
 *
 * `selectedIds` is the raw set and may still contain ids that stopped being
 * selectable after the library changed; `selectedIdsArray` is the filtered
 * intersection to send to the API.
 *
 * @param {object}   params
 * @param {Array}    [params.documents] - Documents of the Data library.
 * @param {Array}    [params.folders] - Folders of the Data library.
 * @param {Set}      [params.attachedIds] - Documents already in the session.
 * @param {Array}    [params.initialSelectedIds] - Ids to preselect.
 * @returns {object} `groups`, `attachedIds`, `documentCount`, `isSelectable`,
 *   `selectedIds`, `selectedIdsArray`, `selectedCount`, `selectedFolderCount`,
 *   `focusedId`, `setFocusedId`, `toggleFolder`, `toggleDocument` and `clear`.
 */
export default function useDocumentFolderSelection({
  documents = [],
  folders = [],
  attachedIds = NO_ATTACHED_IDS,
  initialSelectedIds = [],
} = {}) {
  const [selectedIds, setSelectedIds] = useState(
    () => new Set(initialSelectedIds),
  );
  const [focusedId, setFocusedId] = useState(null);

  const selectableById = useMemo(() => {
    const ids = new Set();
    for (const document of documents) {
      if (
        document.status === DOCUMENT_STATUS.FINISHED &&
        !attachedIds.has(document.id)
      ) {
        ids.add(document.id);
      }
    }
    return ids;
  }, [documents, attachedIds]);

  const isSelectable = useCallback(
    (document) => selectableById.has(document.id),
    [selectableById],
  );

  const groups = useMemo(() => {
    const folderById = new Map(folders.map((folder) => [folder.id, folder]));
    const looseDocuments = [];
    const documentsByFolder = new Map();

    for (const document of documents) {
      const folder =
        document.folder_id != null ? folderById.get(document.folder_id) : null;
      if (!folder) {
        looseDocuments.push(document);
        continue;
      }
      if (!documentsByFolder.has(folder.id)) {
        documentsByFolder.set(folder.id, []);
      }
      documentsByFolder.get(folder.id).push(document);
    }

    const buildGroup = (key, folder, groupDocuments) => {
      const sortedDocuments = [...groupDocuments].sort(compareByName);
      const selectableIds = sortedDocuments
        .filter((document) => selectableById.has(document.id))
        .map((document) => document.id);
      const selectedInGroup = selectableIds.filter((id) => selectedIds.has(id));
      const checked =
        selectableIds.length > 0 &&
        selectedInGroup.length === selectableIds.length;

      return {
        key,
        folder,
        documents: sortedDocuments,
        selectableIds,
        checked,
        indeterminate: !checked && selectedInGroup.length > 0,
        disabled: selectableIds.length === 0,
      };
    };

    const folderGroups = [...folders]
      .filter((folder) => (documentsByFolder.get(folder.id)?.length ?? 0) > 0)
      .sort(compareByName)
      .map((folder) =>
        buildGroup(
          `folder-${folder.id}`,
          folder,
          documentsByFolder.get(folder.id) ?? [],
        ),
      );

    if (looseDocuments.length === 0) return folderGroups;

    return [buildGroup(LOOSE_GROUP_KEY, null, looseDocuments), ...folderGroups];
  }, [documents, folders, selectableById, selectedIds]);

  const selectedIdsArray = useMemo(
    () => [...selectedIds].filter((id) => selectableById.has(id)),
    [selectedIds, selectableById],
  );

  const selectedFolderCount = useMemo(
    () =>
      groups.reduce(
        (count, group) => count + (group.folder && group.checked ? 1 : 0),
        0,
      ),
    [groups],
  );

  /**
   * Selects every selectable document of a group, or clears them all.
   *
   * @param {number|null} folderId - Folder id, or null for loose documents.
   */
  const toggleFolder = useCallback(
    (folderId) => {
      const group = groups.find((candidate) =>
        folderId == null
          ? candidate.folder == null
          : candidate.folder?.id === folderId,
      );
      if (!group || group.disabled) return;

      setSelectedIds((previous) => {
        const next = new Set(previous);
        const allSelected = group.selectableIds.every((id) => next.has(id));
        for (const id of group.selectableIds) {
          if (allSelected) next.delete(id);
          else next.add(id);
        }
        return next;
      });
    },
    [groups],
  );

  /**
   * Adds or removes a single document, if it can be attached.
   *
   * @param {number} documentId - The document id.
   */
  const toggleDocument = useCallback(
    (documentId) => {
      if (!selectableById.has(documentId)) return;
      setSelectedIds((previous) => {
        const next = new Set(previous);
        if (next.has(documentId)) next.delete(documentId);
        else next.add(documentId);
        return next;
      });
    },
    [selectableById],
  );

  const clear = useCallback(() => {
    setSelectedIds(new Set());
    setFocusedId(null);
  }, []);

  return {
    groups,
    attachedIds,
    documentCount: documents.length,
    isSelectable,
    selectedIds,
    selectedIdsArray,
    selectedCount: selectedIdsArray.length,
    selectedFolderCount,
    focusedId,
    setFocusedId,
    toggleFolder,
    toggleDocument,
    clear,
  };
}
