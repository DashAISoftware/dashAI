import { useEffect, useId, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import {
  Box,
  ButtonBase,
  Checkbox,
  Chip,
  Collapse,
  InputAdornment,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import FolderIcon from "@mui/icons-material/Folder";
import FolderOffIcon from "@mui/icons-material/FolderOff";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import { documentStatusChip } from "./documentStatusChip";

/**
 * One selectable document row.
 *
 * @param {object}   props
 * @param {object}   props.doc - The document.
 * @param {object}   props.selection - The selection returned by the hook.
 * @param {boolean}  props.focused - Whether its details are being shown.
 * @param {Function} [props.onFocus] - Called when the row is clicked.
 * @returns {JSX.Element}
 */
function DocumentRow({ doc, selection, focused, onFocus }) {
  const { t } = useTranslation(["generative"]);
  const attached = selection.attachedIds.has(doc.id);
  const selectable = selection.isSelectable(doc);
  const checked = selectable && selection.selectedIds.has(doc.id);
  const chip = documentStatusChip(doc, attached, t);
  const checkboxLabel = chip ? `${doc.name} — ${chip.label}` : doc.name;

  /**
   * Focuses the document and toggles it, if it can be attached.
   */
  const handleSelect = () => {
    onFocus?.(doc);
    selection.toggleDocument(doc.id);
  };

  return (
    <Box
      onClick={handleSelect}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        px: 1,
        py: 0.25,
        minHeight: 44,
        borderRadius: 1,
        cursor: selectable ? "pointer" : "default",
        bgcolor: focused ? "action.selected" : "transparent",
        border: 1,
        borderColor: focused ? "primary.main" : "transparent",
        opacity: selectable ? 1 : 0.75,
        "@media (hover: hover)": {
          "&:hover": {
            bgcolor: focused ? "action.selected" : "action.hover",
          },
        },
        "&:focus-within": {
          outline: "2px solid",
          outlineColor: "primary.main",
          outlineOffset: 2,
        },
      }}
    >
      <Checkbox
        size="small"
        checked={checked}
        disabled={!selectable}
        onChange={handleSelect}
        onFocus={() => onFocus?.(doc)}
        onClick={(event) => event.stopPropagation()}
        slotProps={{ input: { "aria-label": checkboxLabel } }}
        sx={{ p: 0.5 }}
      />
      <Typography
        variant="body2"
        noWrap
        title={doc.name}
        sx={{ flex: 1, minWidth: 0 }}
      >
        {doc.name}
      </Typography>
      {chip && (
        <Chip
          size="small"
          variant="outlined"
          color={chip.color}
          label={chip.label}
          sx={{
            height: 18,
            flexShrink: 0,
            "& .MuiChip-label": { px: 0.75, fontSize: 10 },
          }}
        />
      )}
    </Box>
  );
}

/**
 * One collapsible folder (or the loose-documents group).
 *
 * @param {object}   props
 * @param {object}   props.group - The group derived by the selection hook.
 * @param {object}   props.selection - The selection returned by the hook.
 * @param {boolean}  props.expanded - Whether the documents are visible.
 * @param {boolean}  props.searchActive - Whether a search hides some documents.
 * @param {Function} props.onToggleExpanded - Collapses/expands the group.
 * @param {Function} [props.onFocus] - Called when a document row is clicked.
 * @param {string}   props.contentId - Id of the collapsible content region.
 * @returns {JSX.Element}
 */
function GroupSection({
  group,
  selection,
  expanded,
  searchActive,
  onToggleExpanded,
  onFocus,
  contentId,
}) {
  const { t } = useTranslation(["generative"]);
  const label = group.folder ? group.folder.name : t("documentPicker.noFolder");
  const FolderGlyph = group.folder ? FolderIcon : FolderOffIcon;
  const folderCheckbox = (
    <Checkbox
      size="small"
      checked={group.checked}
      indeterminate={group.indeterminate}
      disabled={group.disabled || searchActive}
      onChange={() => selection.toggleFolder(group.folder?.id ?? null)}
      slotProps={{
        input: {
          "aria-label": t("documentPicker.selectFolder", { name: label }),
        },
      }}
      sx={{ p: 0.75 }}
    />
  );

  return (
    <Box sx={{ opacity: group.disabled ? 0.6 : 1 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          borderRadius: 1,
          "@media (hover: hover)": { "&:hover": { bgcolor: "action.hover" } },
        }}
      >
        <Tooltip
          title={
            searchActive ? t("documentPicker.clearSearchToSelectFolder") : ""
          }
        >
          <span>{folderCheckbox}</span>
        </Tooltip>
        <ButtonBase
          onClick={onToggleExpanded}
          disabled={searchActive}
          aria-expanded={expanded}
          aria-controls={contentId}
          aria-label={t(
            expanded
              ? "documentPicker.collapseFolder"
              : "documentPicker.expandFolder",
            { name: label },
          )}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            flex: 1,
            minWidth: 0,
            minHeight: 44,
            px: 0.5,
            borderRadius: 1,
            textAlign: "left",
            justifyContent: "flex-start",
            "&.Mui-focusVisible": {
              outline: "2px solid",
              outlineColor: "primary.main",
              outlineOffset: 2,
            },
          }}
        >
          <FolderGlyph
            fontSize="small"
            color={group.folder ? "primary" : "disabled"}
          />
          <Typography
            variant="body2"
            noWrap
            title={label}
            sx={{ flex: 1, minWidth: 0, fontWeight: 600 }}
          >
            {label}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("documentPicker.folderCount", {
              count: group.documents.length,
            })}
          </Typography>
          {expanded ? (
            <ExpandMoreIcon fontSize="small" />
          ) : (
            <ChevronRightIcon fontSize="small" />
          )}
        </ButtonBase>
      </Box>

      <Collapse in={expanded} unmountOnExit>
        <Box
          id={contentId}
          role="group"
          aria-label={label}
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 0.25,
            pl: 5,
            pr: 1,
            pb: 0.5,
          }}
        >
          {group.documents.map((doc) => (
            <DocumentRow
              key={doc.id}
              doc={doc}
              selection={selection}
              focused={selection.focusedId === doc.id}
              onFocus={onFocus}
            />
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}

/**
 * Folder-and-document picker over the Data library, without a dialog shell.
 *
 * @param {object}   props
 * @param {object}   props.selection - The selection returned by
 *   `useDocumentFolderSelection`.
 * @param {Function} [props.onFocusDocument] - Called with the clicked document.
 * @returns {JSX.Element}
 */
export default function DocumentFolderPicker({ selection, onFocusDocument }) {
  const { t } = useTranslation(["generative"]);
  const baseId = useId();
  const searchRef = useRef(null);
  const [query, setQuery] = useState("");
  const [collapsedKeys, setCollapsedKeys] = useState(() => new Set());

  useEffect(() => {
    searchRef.current?.focus();
  }, []);

  const needle = query.trim().toLowerCase();
  const visibleGroups = useMemo(() => {
    if (!needle) return selection.groups;
    return selection.groups.reduce((visible, group) => {
      const folderMatches =
        group.folder != null &&
        group.folder.name.toLowerCase().includes(needle);
      const documents = folderMatches
        ? group.documents
        : group.documents.filter((doc) =>
            doc.name.toLowerCase().includes(needle),
          );
      if (documents.length > 0) visible.push({ ...group, documents });
      return visible;
    }, []);
  }, [selection.groups, needle]);

  /**
   * Collapses or expands one group, keeping the rest as they were.
   *
   * @param {string} key - The group key.
   */
  const toggleExpanded = (key) => {
    setCollapsedKeys((previous) => {
      const next = new Set(previous);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const searchActive = needle.length > 0;
  const showEmptyLibrary = selection.documentCount === 0;
  const showNoResults = !showEmptyLibrary && visibleGroups.length === 0;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        minWidth: 0,
        minHeight: 0,
        height: "100%",
      }}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        <TextField
          inputRef={searchRef}
          autoFocus
          size="small"
          fullWidth
          label={t("documentPicker.search")}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />
        {searchActive && (
          <Typography
            variant="caption"
            color="text.secondary"
            role="status"
            aria-live="polite"
          >
            {t("documentPicker.clearSearchToSelectFolder")}
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary" role="status">
          {t("documentPicker.selectedSummary", {
            count: selection.selectedCount,
          })}
        </Typography>
      </Box>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          overscrollBehavior: "contain",
          pr: 0.5,
        }}
      >
        {showEmptyLibrary ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ p: 2, textAlign: "center" }}
          >
            {t("documentPicker.noDocuments")}
          </Typography>
        ) : showNoResults ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ p: 2, textAlign: "center" }}
          >
            {t("documentPicker.noResults")}
          </Typography>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
            {visibleGroups.map((group) => {
              const expanded = searchActive || !collapsedKeys.has(group.key);
              return (
                <GroupSection
                  key={group.key}
                  group={group}
                  selection={selection}
                  expanded={expanded}
                  searchActive={searchActive}
                  onToggleExpanded={() => toggleExpanded(group.key)}
                  onFocus={onFocusDocument}
                  contentId={`${baseId}-${group.key}`}
                />
              );
            })}
          </Box>
        )}
      </Box>
    </Box>
  );
}

DocumentRow.propTypes = {
  doc: PropTypes.object.isRequired,
  selection: PropTypes.object.isRequired,
  focused: PropTypes.bool.isRequired,
  onFocus: PropTypes.func,
};

GroupSection.propTypes = {
  group: PropTypes.object.isRequired,
  selection: PropTypes.object.isRequired,
  expanded: PropTypes.bool.isRequired,
  searchActive: PropTypes.bool.isRequired,
  onToggleExpanded: PropTypes.func.isRequired,
  onFocus: PropTypes.func,
  contentId: PropTypes.string.isRequired,
};

DocumentFolderPicker.propTypes = {
  selection: PropTypes.object.isRequired,
  onFocusDocument: PropTypes.func,
};
