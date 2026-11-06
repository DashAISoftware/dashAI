import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Box,
  ButtonBase,
  Collapse,
  Typography,
  useMediaQuery,
} from "@mui/material";
import FolderIcon from "@mui/icons-material/Folder";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DocumentList from "./DocumentList";

/**
 * Orders session documents into loose ones plus one group per folder.
 *
 * Folders are sorted by name and so are the documents inside each of them, so
 * the panel does not reorder itself when a document is added or detached.
 *
 * @param {Array<object>} documents - Rows carrying `folderId` and `folderName`.
 * @returns {{loose: Array, groups: Array<{id: number, name: string, documents: Array}>}}
 *   The loose documents and the folder groups.
 */
export function groupDocuments(documents) {
  const loose = [];
  const folders = new Map();

  for (const document of documents) {
    if (document.folderId == null) {
      loose.push(document);
      continue;
    }
    const key = String(document.folderId);
    if (!folders.has(key)) {
      folders.set(key, {
        id: document.folderId,
        name: document.folderName ?? "",
        documents: [],
      });
    }
    folders.get(key).documents.push(document);
  }

  const byName = (left, right) =>
    left.name.localeCompare(right.name, undefined, {
      numeric: true,
      sensitivity: "base",
    });
  const groups = Array.from(folders.values())
    .map((group) => ({
      ...group,
      documents: [...group.documents].sort(byName),
    }))
    .sort(byName);

  return { loose: [...loose].sort(byName), groups };
}

/**
 * Renders the session documents grouped by their Data folder.
 *
 * Loose documents keep the flat list at the top; each folder follows as a
 * collapsible section that indents its documents so the grouping is visible
 * at a glance.
 *
 * @param {object}   props
 * @param {Array}    props.documents - Documents of the session.
 * @param {object}   [props.indexStateByDocument] - Indexing state per document.
 * @param {Function} [props.onDocumentClick] - Called with the clicked document.
 * @param {Function} [props.renderActions] - Returns the per-row controls.
 * @returns {JSX.Element} The grouped list.
 */
export default function DocumentGroupList({
  documents,
  indexStateByDocument,
  onDocumentClick,
  renderActions,
}) {
  const { t } = useTranslation("generative");
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const [collapsedFolders, setCollapsedFolders] = useState(() => new Set());
  const { loose, groups } = useMemo(
    () => groupDocuments(documents),
    [documents],
  );

  const listProps = {
    indexStateByDocument,
    onDocumentClick,
    renderActions,
  };

  useEffect(() => {
    const visible = new Set(groups.map((group) => group.id));
    setCollapsedFolders((previous) => {
      const next = new Set([...previous].filter((id) => visible.has(id)));
      return next.size === previous.size ? previous : next;
    });
  }, [groups]);

  const toggleFolder = (folderId) => {
    setCollapsedFolders((previous) => {
      const next = new Set(previous);
      if (next.has(folderId)) next.delete(folderId);
      else next.add(folderId);
      return next;
    });
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        width: "100%",
        minWidth: 0,
        maxWidth: "100%",
      }}
    >
      {loose.length > 0 && <DocumentList documents={loose} {...listProps} />}

      {groups.map((group) => {
        const collapsed = collapsedFolders.has(group.id);
        const folderLabel = group.name || t("documentsBar.untitledFolder");
        return (
          <Box
            key={group.id}
            sx={{ display: "flex", flexDirection: "column", gap: 1 }}
          >
            <ButtonBase
              onClick={() => toggleFolder(group.id)}
              aria-expanded={!collapsed}
              aria-label={
                collapsed
                  ? t("documentsBar.expandFolder", { name: folderLabel })
                  : t("documentsBar.collapseFolder", { name: folderLabel })
              }
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                width: "100%",
                minWidth: 0,
                minHeight: 44,
                px: 1,
                py: 1,
                borderRadius: 1,
                textAlign: "left",
                justifyContent: "flex-start",
                color: "text.secondary",
                "@media (hover: hover)": {
                  "&:hover": { bgcolor: "action.hover" },
                },
                "&.Mui-focusVisible": {
                  outline: "2px solid",
                  outlineColor: "primary.main",
                  outlineOffset: 2,
                },
              }}
            >
              <FolderIcon fontSize="small" color="primary" />
              <Typography
                variant="body2"
                noWrap
                title={folderLabel}
                sx={{
                  flex: 1,
                  minWidth: 0,
                  fontWeight: 600,
                  color: "text.primary",
                }}
              >
                {folderLabel}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("documentsBar.folderDocumentCount", {
                  count: group.documents.length,
                })}
              </Typography>
              {collapsed ? (
                <ChevronRightIcon fontSize="small" />
              ) : (
                <ExpandMoreIcon fontSize="small" />
              )}
            </ButtonBase>

            <Collapse
              in={!collapsed}
              timeout={reduceMotion ? 0 : "auto"}
              unmountOnExit
            >
              <Box sx={{ pl: 2, minWidth: 0 }}>
                <DocumentList documents={group.documents} {...listProps} />
              </Box>
            </Collapse>
          </Box>
        );
      })}
    </Box>
  );
}

DocumentGroupList.propTypes = {
  documents: PropTypes.array.isRequired,
  indexStateByDocument: PropTypes.object,
  onDocumentClick: PropTypes.func,
  renderActions: PropTypes.func,
};
