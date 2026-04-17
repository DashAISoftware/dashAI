import React, { useMemo, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  IconButton,
  InputAdornment,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Stack,
  TextField,
  Tooltip,
  Typography,
  Chip,
  Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import { useCustomComponents } from "./CustomComponentsContext";
import DeleteCustomComponentDialog from "./DeleteCustomComponentDialog";

export default function CustomComponentsLeftBar() {
  const { t } = useTranslation(["customComponents", "common"]);
  const {
    components,
    loadingList,
    listError,
    draft,
    startNewDraft,
    selectComponent,
    remove,
  } = useCustomComponents();
  const [query, setQuery] = useState("");
  const [deleting, setDeleting] = useState(null);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return components;
    return components.filter(
      (c) =>
        c.class_name.toLowerCase().includes(q) ||
        (c.description || "").toLowerCase().includes(q) ||
        c.base_class.toLowerCase().includes(q),
    );
  }, [components, query]);

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
                {query ? t("leftBar.noMatches") : t("emptyState")}
              </Typography>
            </Box>
          ) : (
            <List dense disablePadding>
              {filtered.map((c) => {
                const selected = draft.id === c.id;
                return (
                  <ListItem
                    key={c.id}
                    disablePadding
                    secondaryAction={
                      <Tooltip title={t("actions.delete")}>
                        <IconButton
                          edge="end"
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleting(c);
                          }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    }
                  >
                    <ListItemButton
                      selected={selected}
                      onClick={() => selectComponent(c)}
                      sx={{ pr: 6 }}
                    >
                      <ListItemText
                        primaryTypographyProps={{
                          sx: { fontFamily: "monospace", fontSize: 13 },
                          noWrap: true,
                        }}
                        secondaryTypographyProps={{ noWrap: true }}
                        primary={c.class_name}
                        secondary={
                          <Box
                            component="span"
                            display="flex"
                            gap={0.5}
                            alignItems="center"
                          >
                            <Chip
                              size="small"
                              label={c.base_type}
                              variant="outlined"
                              sx={{ height: 18, fontSize: 10 }}
                            />
                            <Typography
                              variant="caption"
                              color="text.secondary"
                            >
                              {c.base_class}
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
    </SideBar>
  );
}
