import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  CircularProgress,
  InputAdornment,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { useTranslation } from "react-i18next";
import { searchDatasets } from "../../api/hub";
import DatasetCard from "./DatasetCard";

const PAGE_SIZE = 20;

/**
 * Center panel — debounced search bar + paginated grid of DatasetCard components.
 *
 * @param {string|null} sourceName - Active DatasetSource class name.
 * @param {object|null} selectedDataset - Currently selected DatasetEntry.
 * @param {function} onSelectDataset - Called with a DatasetEntry when a card is clicked.
 */
export default function DatasetGrid({ sourceName, selectedDataset, onSelectDataset }) {
  const { t } = useTranslation(["hub", "common"]);
  const [query, setQuery] = useState("");
  const [datasets, setDatasets] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const debounceRef = useRef(null);

  const loadPage = useCallback(
    (q, pageOffset, append) => {
      if (!sourceName) return;
      if (append) setLoadingMore(true);
      else setLoading(true);

      searchDatasets(sourceName, q, PAGE_SIZE, pageOffset)
        .then((results) => {
          setDatasets((prev) => (append ? [...prev, ...results] : results));
          setHasMore(results.length === PAGE_SIZE);
        })
        .catch(() => {
          if (!append) setDatasets([]);
          setHasMore(false);
        })
        .finally(() => {
          if (append) setLoadingMore(false);
          else setLoading(false);
        });
    },
    [sourceName],
  );

  useEffect(() => {
    setDatasets([]);
    setOffset(0);
    setQuery("");
    setHasMore(false);
    if (sourceName) loadPage("", 0, false);
  }, [sourceName]);

  const handleQueryChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    setOffset(0);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadPage(val, 0, false), 400);
  };

  const handleLoadMore = () => {
    const next = offset + PAGE_SIZE;
    setOffset(next);
    loadPage(query, next, true);
  };

  if (!sourceName) {
    return (
      <Box
        sx={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Typography variant="body2" color="text.secondary">
          {t("hub:noSourceSelected")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        p: 2,
        gap: 2,
      }}
    >
      <TextField
        size="small"
        fullWidth
        placeholder={t("hub:searchPlaceholder")}
        value={query}
        onChange={handleQueryChange}
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

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", pt: 4 }}>
          <CircularProgress />
        </Box>
      ) : datasets.length === 0 ? (
        <Box sx={{ display: "flex", justifyContent: "center", pt: 4 }}>
          <Typography variant="body2" color="text.secondary">
            {t("hub:noResults")}
          </Typography>
        </Box>
      ) : (
        <Box sx={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Box
            sx={{
              display: "grid",
              gap: 1.5,
              gridTemplateColumns: {
                xs: "1fr",
                md: "repeat(2, 1fr)",
                xl: "repeat(3, 1fr)",
              },
              alignContent: "start",
            }}
          >
            {datasets.map((ds) => (
              <DatasetCard
                key={ds.id}
                dataset={ds}
                selected={selectedDataset?.id === ds.id}
                onSelect={() => onSelectDataset(ds)}
              />
            ))}
          </Box>

          {hasMore && (
            <Box sx={{ display: "flex", justifyContent: "center", py: 1 }}>
              {loadingMore ? (
                <CircularProgress size={24} />
              ) : (
                <Button size="small" onClick={handleLoadMore}>
                  {t("common:viewMore")}
                </Button>
              )}
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}
