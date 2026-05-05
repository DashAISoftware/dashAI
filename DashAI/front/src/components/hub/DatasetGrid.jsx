import { useCallback, useEffect, useRef, useState } from "react";
import {
  Box,
  CircularProgress,
  InputAdornment,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { useTranslation } from "react-i18next";
import { searchDatasets } from "../../api/hub";
import DatasetCard from "./DatasetCard";

/**
 * Center panel — debounced search bar + grid of DatasetCard components.
 *
 * @param {string|null} sourceName - Active DatasetSource class name.
 * @param {object|null} selectedDataset - Currently selected DatasetEntry.
 * @param {function} onSelectDataset - Called with a DatasetEntry when a card is clicked.
 */
export default function DatasetGrid({ sourceName, selectedDataset, onSelectDataset }) {
  const { t } = useTranslation(["hub"]);
  const [query, setQuery] = useState("");
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  const fetchDatasets = useCallback(
    (q) => {
      if (!sourceName) return;
      setLoading(true);
      searchDatasets(sourceName, q, 40)
        .then(setDatasets)
        .catch(() => setDatasets([]))
        .finally(() => setLoading(false));
    },
    [sourceName],
  );

  useEffect(() => {
    setDatasets([]);
    setQuery("");
    if (sourceName) fetchDatasets("");
  }, [sourceName]);

  const handleQueryChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchDatasets(val), 400);
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
        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
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
      )}
    </Box>
  );
}
