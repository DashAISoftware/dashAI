import { getNextAvailableName } from "../../../../utils/nameGenerator";
import {
  MAX_FILE_SIZE_BYTES,
  SKIP_REASON,
  SYSTEM_FILE_NAMES,
} from "./uploadConstants";

/**
 * File selection helpers for the RAG upload dialog.
 *
 * A selection is an array of entries, each one a real `File` plus the path it
 * had in the picked folder (`relativePath`). The path is what lets the dialog
 * show where a nested file came from and derive the root folder name.
 */

/**
 * Returns the lowercase extension of a file name, including the leading dot.
 *
 * @param {string} fileName - The file name, e.g. "Report.PDF".
 * @returns {string} ".pdf", or "" when the name has no extension.
 */
export function getFileExtension(fileName) {
  const dot = fileName.lastIndexOf(".");
  if (dot <= 0) return "";
  return fileName.slice(dot).toLowerCase();
}

/**
 * Reads the path a file had inside the picked folder.
 *
 * `webkitRelativePath` is only filled by `<input webkitdirectory>` and by
 * drop entries; a plain multi-file pick falls back to the bare name.
 *
 * @param {File} file - The picked file.
 * @returns {string} The relative path.
 */
export function getRelativePath(file) {
  return file.webkitRelativePath || file.name;
}

/**
 * True when any segment of the path starts with a dot, which is how both
 * macOS (`__MACOSX`, `.DS_Store`) and Unix mark hidden content.
 *
 * @param {string} relativePath - The path to inspect.
 * @returns {boolean} Whether the path is hidden.
 */
function isHiddenPath(relativePath) {
  return relativePath.split("/").some((segment) => segment.startsWith("."));
}

/**
 * True for the junk files Windows, macOS and Office write into every folder.
 *
 * Office keeps its lock files next to the document while it is open
 * (`~$report.docx`); uploading those would create a broken duplicate.
 *
 * @param {string} fileName - The file name.
 * @returns {boolean} Whether it is a known system file.
 */
function isSystemFile(fileName) {
  return (
    fileName.startsWith("~$") ||
    SYSTEM_FILE_NAMES.includes(fileName.toLowerCase())
  );
}

/**
 * Drops the files that must never reach a document loader.
 *
 * @param {Array<{file: File, relativePath: string}>} entries - The selection.
 * @returns {{accepted: Array, skipped: Array<{relativePath: string, reason: string}>}}
 *   The files to upload and, for each dropped one, the reason it was dropped.
 */
export function filterEntries(entries) {
  const accepted = [];
  const skipped = [];

  for (const entry of entries) {
    const { file, relativePath } = entry;

    if (isHiddenPath(relativePath)) {
      skipped.push({ relativePath, reason: SKIP_REASON.HIDDEN });
      continue;
    }
    if (isSystemFile(file.name)) {
      skipped.push({ relativePath, reason: SKIP_REASON.SYSTEM });
      continue;
    }
    if (file.size === 0) {
      skipped.push({ relativePath, reason: SKIP_REASON.EMPTY });
      continue;
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      skipped.push({ relativePath, reason: SKIP_REASON.TOO_LARGE });
      continue;
    }

    accepted.push(entry);
  }

  return { accepted, skipped };
}

/**
 * Turns the `FileList` of an `<input type="file">` into a filtered selection.
 *
 * @param {FileList|null} fileList - The input's files.
 * @returns {{accepted: Array, skipped: Array}} The accepted and skipped entries.
 */
export function readSelectedFiles(fileList) {
  const entries = Array.from(fileList ?? []).map((file) => ({
    file,
    relativePath: getRelativePath(file),
  }));
  return filterEntries(entries);
}

/**
 * Reads every child of a directory entry, draining the reader.
 *
 * `readEntries` returns at most 100 children per call, so a single call would
 * silently truncate a large folder.
 *
 * @param {FileSystemDirectoryReader} reader - The directory reader.
 * @returns {Promise<FileSystemEntry[]>} All children.
 */
async function readAllDirectoryEntries(reader) {
  const children = [];
  for (;;) {
    const batch = await new Promise((resolve, reject) => {
      reader.readEntries(resolve, reject);
    });
    if (batch.length === 0) return children;
    children.push(...batch);
  }
}

/**
 * Resolves a drop entry into the file it points at.
 *
 * @param {FileSystemFileEntry} entry - The file entry.
 * @returns {Promise<File>} The underlying file.
 */
function readEntryFile(entry) {
  return new Promise((resolve, reject) => {
    entry.file(resolve, reject);
  });
}

/**
 * Walks one dropped entry, collecting files with their path from the root.
 *
 * A file or folder the browser cannot read is recorded as skipped and the rest
 * of the drop keeps going: one unreadable item must not discard the selection.
 *
 * @param {FileSystemEntry} entry - File or directory entry.
 * @param {string} parentPath - Path of the folder this entry lives in.
 * @param {Array<{file: File, relativePath: string}>} collected - Accepted files.
 * @param {Array<{relativePath: string, reason: string}>} unreadable - Failures.
 * @returns {Promise<void>} Resolves once the whole subtree is read.
 */
async function collectEntry(entry, parentPath, collected, unreadable) {
  if (entry.isFile) {
    try {
      const file = await readEntryFile(entry);
      collected.push({ file, relativePath: `${parentPath}${file.name}` });
    } catch {
      unreadable.push({
        relativePath: `${parentPath}${entry.name}`,
        reason: SKIP_REASON.READ_ERROR,
      });
    }
    return;
  }
  if (!entry.isDirectory) return;

  const directoryPath = `${parentPath}${entry.name}/`;
  let children;
  try {
    children = await readAllDirectoryEntries(entry.createReader());
  } catch {
    unreadable.push({
      relativePath: directoryPath,
      reason: SKIP_REASON.READ_ERROR,
    });
    return;
  }
  for (const child of children) {
    await collectEntry(child, directoryPath, collected, unreadable);
  }
}

/**
 * Reads a drag & drop, which can contain files and whole folders.
 *
 * The entries API is what exposes folders at all; browsers without it (or a
 * drop that only carries files) fall back to `dataTransfer.files`, which is
 * flat but still usable.
 *
 * @param {DataTransfer} dataTransfer - The drop payload.
 * @returns {Promise<{accepted: Array, skipped: Array, hasDirectory: boolean}>}
 *   The filtered selection plus whether a folder was part of the drop.
 */
export async function readDroppedEntries(dataTransfer) {
  const items = Array.from(dataTransfer?.items ?? []);
  // `webkitGetAsEntry` has to run synchronously, while the drop event is still
  // being dispatched; after the first await the items list is emptied.
  const rootEntries = items
    .filter((item) => item.kind === "file")
    .map((item) => item.webkitGetAsEntry?.())
    .filter(Boolean);

  if (rootEntries.length === 0) {
    return { ...readSelectedFiles(dataTransfer?.files), hasDirectory: false };
  }

  const collected = [];
  const unreadable = [];
  for (const entry of rootEntries) {
    await collectEntry(entry, "", collected, unreadable);
  }

  const filtered = filterEntries(collected);
  return {
    accepted: filtered.accepted,
    skipped: [...filtered.skipped, ...unreadable],
    hasDirectory: rootEntries.some((entry) => entry.isDirectory),
  };
}

/**
 * Groups entries by lowercase extension.
 *
 * @param {Array<{file: File, relativePath: string}>} entries - The selection.
 * @returns {Record<string, Array>} A map from ".pdf" (or "" when there is no
 *   extension) to the entries carrying it.
 */
export function groupByExtension(entries) {
  const groups = {};
  for (const entry of entries) {
    const extension = getFileExtension(entry.file.name);
    if (!groups[extension]) groups[extension] = [];
    groups[extension].push(entry);
  }
  return groups;
}

/**
 * Returns the name of the folder the whole selection came from.
 *
 * @param {Array<{relativePath: string}>} entries - The selection.
 * @returns {string} The root folder name, or "" when the files were picked
 *   individually (their paths have no folder segment).
 */
export function getRootFolderName(entries) {
  for (const entry of entries) {
    const [root, ...rest] = entry.relativePath.split("/");
    if (rest.length > 0) return root;
  }
  return "";
}

/**
 * Returns every distinct root folder present in the selection.
 *
 * A drop can carry more than one folder, or a folder plus loose files; the
 * upload still places everything in a single folder, so callers use this to
 * tell the user that several roots were merged.
 *
 * @param {Array<{relativePath: string}>} entries - The selection.
 * @returns {Array<string>} Unique root names; empty when every file was picked
 *   individually.
 */
export function getRootFolderNames(entries) {
  const roots = new Set();
  for (const entry of entries) {
    const [root, ...rest] = entry.relativePath.split("/");
    if (rest.length > 0) roots.add(root);
  }
  return [...roots];
}

/**
 * Returns `base`, suffixed only if it is already taken.
 *
 * @param {string} base - The desired name.
 * @param {Set<string>} usedNames - Names already in use (documents, folders or
 *   both, depending on the caller).
 * @returns {string} A name that is not in `usedNames`.
 */
export function uniqueName(base, usedNames) {
  const normalized = base?.trim() ?? "";
  if (!normalized) return normalized;
  if (!usedNames.has(normalized)) return normalized;
  return getNextAvailableName(
    normalized,
    Array.from(usedNames, (name) => ({ name })),
  );
}
