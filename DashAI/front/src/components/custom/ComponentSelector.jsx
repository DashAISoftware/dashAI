import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Stack,
  TextField,
  InputAdornment,
  IconButton,
  Chip,
  Typography,
  Collapse,
  Paper,
} from "@mui/material";
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandMoreIcon,
  Check as CheckIcon,
} from "@mui/icons-material";
import { useTranslation } from "react-i18next";

const ALL_CATEGORY = "All";

function getLabel(component) {
  return component.display_name || component.name;
}

function getDescription(component, fallback = "") {
  return component.description ?? fallback;
}

function ComponentSelector({
  components,
  selected = null,
  onSelect,
  categoryKey = "type",
  searchPlaceholder,
  emptyText,
  getIcon,
  tourDataFor = null,
}) {
  const { t } = useTranslation("custom");
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState(ALL_CATEGORY);

  const categories = useMemo(() => {
    const set = new Set();
    components.forEach((c) => {
      const cat = c[categoryKey];
      if (cat) set.add(cat);
    });
    return [ALL_CATEGORY, ...Array.from(set).sort()];
  }, [components, categoryKey]);

  const [expanded, setExpanded] = useState(() => new Set(categories));

  React.useEffect(() => {
    setExpanded(new Set(categories));
  }, [categories]);

  const toggleCategory = (cat) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return components.filter((c) => {
      const matchesCategory =
        activeCategory === ALL_CATEGORY || c[categoryKey] === activeCategory;
      if (!matchesCategory) return false;
      if (q === "") return true;
      const label = getLabel(c).toLowerCase();
      const desc = getDescription(c, t("noDescriptionAvailable")).toLowerCase();
      return label.includes(q) || desc.includes(q);
    });
  }, [components, search, activeCategory, categoryKey]);

  const grouped = useMemo(() => {
    const groups = {};
    filtered.forEach((c) => {
      const cat = c[categoryKey] || "Other";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(c);
    });
    return groups;
  }, [filtered, categoryKey]);

  const counts = useMemo(() => {
    const map = {};
    components.forEach((c) => {
      const cat = c[categoryKey];
      if (cat) map[cat] = (map[cat] || 0) + 1;
    });
    return map;
  }, [components, categoryKey]);

  const handleSelect = (component) => onSelect?.(component);

  return (
    <Stack direction="column" sx={{ height: "100%", minHeight: 0 }} spacing={2}>
      <TextField
        size="small"
        fullWidth
        placeholder={searchPlaceholder ?? t("search")}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: search ? (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearch("")}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : null,
          },
        }}
      />

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {categories.map((cat) => {
          const isActive = activeCategory === cat;
          const count = cat === ALL_CATEGORY ? components.length : counts[cat];
          return (
            <Chip
              key={cat}
              label={`${cat} (${count})`}
              clickable
              color={isActive ? "primary" : "default"}
              variant={isActive ? "filled" : "outlined"}
              onClick={() => setActiveCategory(cat)}
              size="small"
            />
          );
        })}
      </Stack>

      <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto", pr: 1 }}>
        <Stack spacing={1.5}>
          {Object.entries(grouped).map(([cat, items]) => {
            const isOpen = expanded.has(cat);
            return (
              <Box key={cat}>
                <Box
                  onClick={() => toggleCategory(cat)}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    py: 1,
                    cursor: "pointer",
                    color: "text.secondary",
                    "&:hover": { color: "text.primary" },
                  }}
                >
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Typography
                      variant="overline"
                      sx={{ letterSpacing: 1, fontWeight: 600 }}
                    >
                      {cat}
                    </Typography>
                    <Chip label={items.length} size="small" />
                  </Stack>
                  <ExpandMoreIcon
                    fontSize="small"
                    sx={{
                      transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
                      transition: "transform 0.2s",
                    }}
                  />
                </Box>
                <Collapse in={isOpen} unmountOnExit>
                  <Box
                    sx={{
                      display: "grid",
                      gap: 1,
                      gridTemplateColumns: {
                        xs: "1fr",
                        md: "repeat(2, 1fr)",
                        xl: "repeat(3, 1fr)",
                      },
                      pt: 1,
                    }}
                  >
                    {items.map((component) => {
                      const isSelected = selected?.name === component.name;
                      const icon = getIcon?.(component);
                      const isCsvComponent =
                        tourDataFor &&
                        component.name.toLowerCase().includes("csv");
                      return (
                        <Paper
                          key={component.name}
                          elevation={0}
                          onClick={() => handleSelect(component)}
                          data-tour={isCsvComponent ? tourDataFor : undefined}
                          sx={{
                            p: 1.5,
                            display: "flex",
                            gap: 1.5,
                            alignItems: "flex-start",
                            cursor: "pointer",
                            border: 1,
                            borderColor: isSelected
                              ? "primary.main"
                              : "divider",
                            bgcolor: isSelected
                              ? "action.selected"
                              : "background.paper",
                            transition: "border-color 0.15s, background 0.15s",
                            "&:hover": {
                              borderColor: "primary.light",
                            },
                          }}
                        >
                          {icon && (
                            <Box
                              sx={{
                                p: 1,
                                borderRadius: 1,
                                bgcolor: isSelected
                                  ? "primary.main"
                                  : "action.hover",
                                color: isSelected
                                  ? "primary.contrastText"
                                  : "text.primary",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexShrink: 0,
                              }}
                            >
                              {icon}
                            </Box>
                          )}
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Typography
                              variant="subtitle2"
                              noWrap
                              sx={{ fontWeight: 600 }}
                            >
                              {getLabel(component)}
                            </Typography>
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{
                                display: "-webkit-box",
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: "vertical",
                                overflow: "hidden",
                                mt: 0.5,
                              }}
                            >
                              {getDescription(
                                component,
                                t("noDescriptionAvailable"),
                              )}
                            </Typography>
                          </Box>
                          {isSelected && (
                            <CheckIcon
                              fontSize="small"
                              color="primary"
                              sx={{ flexShrink: 0, mt: 0.5 }}
                            />
                          )}
                        </Paper>
                      );
                    })}
                  </Box>
                </Collapse>
              </Box>
            );
          })}

          {filtered.length === 0 && (
            <Box
              sx={{
                textAlign: "center",
                py: 6,
                color: "text.secondary",
              }}
            >
              <SearchIcon sx={{ fontSize: 48, opacity: 0.4, mb: 1 }} />
              <Typography variant="body2">
                {emptyText ?? t("noItemsFound")}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.7 }}>
                {t("tryAdjustingSearch")}
              </Typography>
            </Box>
          )}
        </Stack>
      </Box>

      <Box
        sx={{
          pt: 1.5,
          borderTop: 1,
          borderColor: "divider",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          {t("componentsAvailable", { count: filtered.length })}
        </Typography>
        {selected && (
          <Chip
            icon={<CheckIcon />}
            label={getLabel(selected)}
            color="primary"
            variant="outlined"
            size="small"
          />
        )}
      </Box>
    </Stack>
  );
}

ComponentSelector.propTypes = {
  components: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.string,
      description: PropTypes.string,
      schema: PropTypes.object,
    }),
  ).isRequired,
  selected: PropTypes.shape({ name: PropTypes.string }),
  onSelect: PropTypes.func.isRequired,
  categoryKey: PropTypes.string,
  searchPlaceholder: PropTypes.string,
  emptyText: PropTypes.string,
  getIcon: PropTypes.func,
};

export default ComponentSelector;
