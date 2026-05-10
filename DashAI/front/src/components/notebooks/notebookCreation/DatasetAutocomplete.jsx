import React, { useEffect, useState } from "react";
import { Box, Typography, Autocomplete, TextField, Chip } from "@mui/material";
import { formatDate } from "../../../pages/results/constants/formatDate";
import { getDatasetInfo } from "../../../api/datasets";
import { useTranslation } from "react-i18next";

export default function DatasetAutocomplete({
  datasets,
  selectedDataset,
  setSelectedDataset,
}) {
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [infoError, setInfoError] = useState(null);
  const [infosById, setInfosById] = useState({});
  const { t } = useTranslation(["datasets", "common"]);

  // Fetch info for selected dataset (detail panel)
  useEffect(() => {
    let cancelled = false;
    const fetchInfo = async () => {
      if (!selectedDataset?.id) {
        setDatasetInfo(null);
        setInfoError(null);
        return;
      }
      try {
        setLoadingInfo(true);
        setInfoError(null);
        const info = await getDatasetInfo(selectedDataset.id);
        if (!cancelled) setDatasetInfo(info);
      } catch (e) {
        console.error("Failed to fetch dataset info:", e);
        if (!cancelled)
          setInfoError(t("datasets:error.failedToLoadDatasetInfo"));
      } finally {
        if (!cancelled) setLoadingInfo(false);
      }
    };
    fetchInfo();
    return () => {
      cancelled = true;
    };
  }, [selectedDataset?.id]);

  const fetchMissingInfos = async (items) => {
    const missing = items.filter((d) => d?.id != null && !infosById[d.id]);
    if (missing.length === 0) return;
    try {
      const results = await Promise.allSettled(
        missing.map((d) => getDatasetInfo(d.id)),
      );
      const map = {};
      results.forEach((res, idx) => {
        const id = missing[idx]?.id;
        if (res.status === "fulfilled" && id != null) {
          map[id] = res.value;
        }
      });
      setInfosById((prev) => ({ ...prev, ...map }));
    } catch (e) {
      console.warn("Some dataset infos could not be fetched", e);
    }
  };

  useEffect(() => {
    if (!datasets || datasets.length === 0) return;
  }, [datasets]);

  return (
    <Box width="100%">
      <Box sx={{ width: "100%", mx: "auto" }}>
        <Autocomplete
          data-tour="models-dataset-selection"
          options={datasets}
          getOptionLabel={(option) => option.name}
          isOptionEqualToValue={(opt, val) => opt.id === val.id}
          value={selectedDataset}
          onOpen={() => fetchMissingInfos(datasets)}
          onChange={(event, newValue) => {
            setSelectedDataset(newValue);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("datasets:label.selectDataset")}
              variant="outlined"
              placeholder={t("datasets:label.typeToSearchDatasets")}
            />
          )}
          renderOption={(props, option) => {
            const { key, ...rootProps } = props;
            const info = infosById[option.id];
            return (
              <Box component="li" key={key} {...rootProps}>
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    width: "100%",
                    gap: 1,
                  }}
                >
                  <Typography variant="body1" fontWeight="medium">
                    {option.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("common:created")}: {formatDate(option.created)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("datasets:label.rowsColumnsInfo", {
                      totalRows: info ? info.total_rows : "...",
                      totalColumns: info ? info.total_columns : "...",
                    })}
                  </Typography>
                </Box>
              </Box>
            );
          }}
          sx={{ mb: 6 }}
        />

        {selectedDataset && (
          <Box
            sx={{
              mt: 6,
              p: 6,
              border: 1,
              borderColor: "divider",
              borderRadius: 2,
            }}
          >
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Typography variant="body2" fontWeight="medium">
                  {t("common:name")}:
                </Typography>
                <Chip label={selectedDataset.name} size="small" />
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Typography variant="body2" fontWeight="medium">
                  {t("common:created")}:
                </Typography>
                <Typography variant="body2">
                  {formatDate(selectedDataset.created)}
                </Typography>
              </Box>
              {/* Single line for Rows | Columns */}
              <Typography variant="body2" fontWeight="medium">
                {t("datasets:label.rowsColumnsInfo", {
                  totalRows: datasetInfo
                    ? datasetInfo.total_rows
                    : t("common:loading"),
                  totalColumns: datasetInfo
                    ? datasetInfo.total_columns
                    : t("common:loading"),
                })}
              </Typography>
              {infoError && (
                <Typography variant="caption" color="error">
                  {infoError}
                </Typography>
              )}
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
}
