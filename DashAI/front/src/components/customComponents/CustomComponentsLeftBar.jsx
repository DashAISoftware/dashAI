import React, { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  InputAdornment,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import UndoIcon from "@mui/icons-material/Undo";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { useCustomComponents } from "./CustomComponentsContext";
import DeleteCustomComponentDialog from "./DeleteCustomComponentDialog";

const FILTERS = [
  { key: "all", match: () => true },
  { key: "modified", match: (it) => it.origin === "custom-override" },
  { key: "custom", match: (it) => it.origin === "custom" },
  { key: "core", match: (it) => it.origin === "core" },
];

function originChipProps(origin, t) {
  switch (origin) {
    case "custom":
      return { label: t("origin.custom"), color: "primary" };
    case "custom-override":
      return { label: t("origin.modified"), color: "warning" };
    case "core":
      return { label: t("origin.core"), color: "default" };
    case "plugin":
      return { label: t("origin.plugin"), color: "secondary" };
    default:
      return { label: origin, color: "default" };
  }
}

export default function CustomComponentsLeftBar() {
  const { t } = useTranslation(["customComponents", "common"]);
  const {
    items,
    loadingList,
    listError,
    draft,
    startNewDraft,
    selectComponent,
    remove,
  } = useCustomComponents();

  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [deleting, setDeleting] = useState(null);
  const [reverting, setReverting] = useState(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filterFn =
      FILTERS.find((f) => f.key === filter)?.match || FILTERS[0].match;
    return items
      .filter(filterFn)
      .filter(
        (c) =>
          !q ||
          c.name.toLowerCase().includes(q) ||
          (c.customRow?.description || "").toLowerCase().includes(q) ||
          c.base_type.toLowerCase().includes(q),
      )
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [items, filter, query]);

  return (
    <SideBar>
      <Box display="flex" flexDirection="column" height="100%">
        <Box p={1.5} borderBottom="1px solid" borderColor="divider">
          <Stack direction="row" alignItems="center" mb={1} spacing={1}>
            <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
              {t("leftBar.title")}
            </Typography>
            <Tooltip title={t("actions.new")}>
              <IconButton
                size="small"
                color="primary"
                onClick={startNewDraft}
                aria-label={t("actions.new")}
              >
                <AddIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
          <TextField
            fullWidth
            size="small"
            placeholder={t("leftBar.searchPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
        </Box>

        <Tabs
          value={filter}
          onChange={(_, v) => setFilter(v)}
          variant="fullWidth"
          sx={{
            minHeight: 32,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          {FILTERS.map((f) => (
            <Tab
              key={f.key}
              value={f.key}
              label={t(`leftBar.filters.${f.key}`)}
              sx={{ minHeight: 32, fontSize: 11, minWidth: 0 }}
            />
          ))}
        </Tabs>

        <Box flexGrow={1} overflow="auto">
          {listError && (
            <Alert severity="error" sx={{ m: 1 }}>
              {listError}
            </Alert>
          )}
          {loadingList ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress size={20} />
            </Box>
          ) : filtered.length === 0 ? (
            <Box p={2} textAlign="center">
              <Typography variant="body2" color="text.secondary">
                {query ? t("leftBar.noMatches") : t("leftBar.empty")}
              </Typography>
            </Box>
          ) : (
            <List dense disablePadding>
              {filtered.map((c) => {
                const selected =
                  draft.id != null
                    ? draft.id === c.customRow?.id
                    : draft.class_name === c.name;
                const isOverride = c.origin === "custom-override";
                const isCustomOnly = c.origin === "custom";
                const chip = originChipProps(c.origin, t);
                return (
                  <ListItem
                    key={c.name}
                    disablePadding
                    secondaryAction={
                      isOverride ? (
                        <Tooltip title={t("actions.revert")}>
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              setReverting(c.customRow);
                            }}
                          >
                            <UndoIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      ) : isCustomOnly ? (
                        <Tooltip title={t("actions.delete")}>
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleting(c.customRow);
                            }}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      ) : null
                    }
                  >
                    <ListItemButton
                      selected={selected}
                      onClick={() => selectComponent(c)}
                      sx={{ pr: isOverride || isCustomOnly ? 6 : 2 }}
                    >
                      <ListItemText
                        primaryTypographyProps={{
                          sx: { fontFamily: "monospace", fontSize: 13 },
                          noWrap: true,
                        }}
                        secondaryTypographyProps={{ noWrap: true }}
                        primary={c.name}
                        secondary={
                          <Box
                            component="span"
                            display="flex"
                            gap={0.5}
                            alignItems="center"
                          >
                            <Chip
                              size="small"
                              variant={
                                chip.color === "default" ? "outlined" : "filled"
                              }
                              color={chip.color}
                              label={chip.label}
                              sx={{ height: 16, fontSize: 10 }}
                            />
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              noWrap
                            >
                              {c.base_type}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          )}
        </Box>

        <Box p={1.5} borderTop="1px solid" borderColor="divider">
          <Button
            fullWidth
            size="small"
            variant="contained"
            startIcon={<AddIcon />}
            onClick={startNewDraft}
          >
            {t("actions.new")}
          </Button>
        </Box>
      </Box>

      <DeleteCustomComponentDialog
        component={deleting}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          await remove(deleting);
          setDeleting(null);
        }}
      />
      <DeleteCustomComponentDialog
        component={reverting}
        revert
        onClose={() => setReverting(null)}
        onConfirm={async () => {
          await remove(reverting, { isRevert: true });
          setReverting(null);
        }}
      />
    </SideBar>
  );
}
