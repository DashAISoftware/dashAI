import React from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  Chip,
  Divider,
  InputAdornment,
  MenuItem,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import SearchIcon from "@mui/icons-material/Search";
import GridViewIcon from "@mui/icons-material/GridView";
import ViewListIcon from "@mui/icons-material/ViewList";
import { useTranslation } from "react-i18next";
import { SectionLabel } from "./PluginParts";
import {
  NO_FILTERS,
  STATUS_FILTERS,
  SOURCES,
  matchesOrigin,
  matchesStatus,
  originFilters,
} from "../pluginUtils";

const SORTS = ["newest", "oldest", "name"];

function Field({ label, children, grow }) {
  return (
    <Box sx={{ flexGrow: grow ? 1 : 0, minWidth: grow ? 220 : 160 }}>
      <SectionLabel>{label}</SectionLabel>
      {children}
    </Box>
  );
}
Field.propTypes = {
  label: PropTypes.string,
  children: PropTypes.node,
  grow: PropTypes.bool,
};

export default function PluginsToolbar({
  plugins,
  updates,
  filters,
  onFiltersChange,
  sortBy,
  onSortByChange,
  view,
  onViewChange,
  shown,
  tab,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["plugins"]);
  const set = (change) => onFiltersChange({ ...filters, ...change });
  // The selected tag always shows, even if no plugin matches it
  const tags = [
    ...new Set([...plugins.flatMap((p) => p.component_types), filters.tag]),
  ]
    .filter(Boolean)
    .sort();

  const statusChips = STATUS_FILTERS[tab]
    .map((status) => ({
      key: status,
      count: plugins.filter((p) => matchesStatus(p, status, updates)).length,
    }))
    .filter(
      ({ key, count }) =>
        count > 0 ||
        filters.status === key ||
        !["warnings", "updates"].includes(key),
    );
  const originChips =
    tab === "installed"
      ? originFilters(plugins, filters.origin).map((origin) => ({
          key: origin,
          count: plugins.filter((p) => matchesOrigin(p, origin)).length,
        }))
      : [];
  const filtered = Object.keys(NO_FILTERS).some(
    (key) => filters[key] !== NO_FILTERS[key],
  );

  const chip = (group, { key, count }) => {
    const selected = filters[group] === key;
    return (
      <Chip
        key={key}
        label={`${t(`plugins:filter.${group}.${key}`, {
          defaultValue: SOURCES[key]?.name ?? key,
        })} (${count})`}
        onClick={() => set({ [group]: key })}
        variant="outlined"
        color={selected ? "primary" : "default"}
        sx={
          selected ? { bgcolor: `${theme.palette.primary.main}14` } : undefined
        }
      />
    );
  };

  return (
    <Box sx={{ mb: 3 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 2,
          alignItems: "flex-end",
        }}
      >
        <Field label={t("plugins:label.search")} grow>
          <TextField
            size="small"
            fullWidth
            value={filters.search}
            placeholder={t("plugins:label.searchPlaceholder")}
            onChange={(event) => set({ search: event.target.value })}
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
        </Field>
        <Field label={t("plugins:label.tags")}>
          <TextField
            select
            size="small"
            fullWidth
            value={filters.tag}
            onChange={(event) => set({ tag: event.target.value })}
            slotProps={{ select: { displayEmpty: true } }}
          >
            <MenuItem value="">{t("plugins:label.allTags")}</MenuItem>
            {tags.map((tag) => (
              <MenuItem key={tag} value={tag}>
                {tag}
              </MenuItem>
            ))}
          </TextField>
        </Field>
        <Field label={t("plugins:label.sortBy")}>
          <TextField
            select
            size="small"
            fullWidth
            value={sortBy}
            onChange={(event) => onSortByChange(event.target.value)}
          >
            {SORTS.map((sort) => (
              <MenuItem key={sort} value={sort}>
                {t(`plugins:sort.${sort}`)}
              </MenuItem>
            ))}
          </TextField>
        </Field>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={view}
          onChange={(event, value) => value && onViewChange(value)}
        >
          <ToggleButton value="grid" aria-label={t("plugins:label.gridView")}>
            <GridViewIcon fontSize="small" />
          </ToggleButton>
          <ToggleButton value="list" aria-label={t("plugins:label.listView")}>
            <ViewListIcon fontSize="small" />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 1,
          alignItems: "center",
          mt: 2,
          // Chip height, so "Clear filters" appearing doesn't move the cards
          minHeight: 32,
        }}
      >
        {statusChips.map((item) => chip("status", item))}
        {statusChips.length > 0 && originChips.length > 0 && (
          <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
        )}
        {originChips.map((item) => chip("origin", item))}
        {filtered && (
          <Button size="small" onClick={() => onFiltersChange(NO_FILTERS)}>
            {t("plugins:button.clearFilters")}
          </Button>
        )}
        <Box sx={{ flexGrow: 1 }} />
        <Typography
          sx={{ ...theme.typography.tabLabel, color: "text.secondary" }}
        >
          {t("plugins:label.count", { count: shown })}
        </Typography>
      </Box>
    </Box>
  );
}

PluginsToolbar.propTypes = {
  plugins: PropTypes.array.isRequired,
  updates: PropTypes.object.isRequired,
  filters: PropTypes.object.isRequired,
  onFiltersChange: PropTypes.func.isRequired,
  sortBy: PropTypes.string.isRequired,
  onSortByChange: PropTypes.func.isRequired,
  view: PropTypes.string.isRequired,
  onViewChange: PropTypes.func.isRequired,
  shown: PropTypes.number.isRequired,
  tab: PropTypes.oneOf(Object.keys(STATUS_FILTERS)).isRequired,
};
