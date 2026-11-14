import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  CircularProgress,
  InputAdornment,
  Radio,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";
import ExportBreadcrumbs from "./ExportBreadcrumbs";

const STATUS_COLOR = {
  compatible: "success.main",
  warning: "warning.main",
  incompatible: "error.main",
};

/**
 * Second step of the dataset export flow: choose the dataset to publish.
 *
 * Lists the finished datasets with how well each fits the chosen platform.
 * Incompatible datasets are shown but cannot be selected; a warning means the
 * dataset can be exported without some of its columns.
 *
 * @param {string} platformName - Display name of the chosen platform.
 * @param {Array<object>} datasets - Exportable datasets with their compatibility.
 * @param {boolean} loading - Whether the dataset list is still loading.
 * @param {boolean} error - Whether the dataset list failed to load.
 * @param {object|null} selected - The dataset currently selected.
 * @param {function} onSelect - Called with the clicked dataset.
 * @param {function} onBack - Returns to the platform step.
 * @param {function} onNext - Continues with the selected dataset.
 */
export default function ExportDatasetStep({
  platformName,
  datasets,
  loading,
  error,
  selected,
  onSelect,
  onBack,
  onNext,
}) {
  const { t } = useTranslation(["export"]);
  const [search, setSearch] = useState("");

  const visibleDatasets = useMemo(() => {
    const query = search.trim().toLowerCase();
    return query
      ? datasets.filter((d) => d.name.toLowerCase().includes(query))
      : datasets;
  }, [datasets, search]);

  const exportableCount = datasets.filter(
    (d) => d.compatibility.status !== "incompatible",
  ).length;

  const describe = ({ status, unsupported_columns: columns }) => {
    const joined = columns.join(", ");
    if (status === "compatible") return t("export:compatible");
    if (status === "warning") {
      return t("export:columnsLeftOut", { columns: joined });
    }
    return columns.length
      ? t("export:incompatibleColumns", { columns: joined })
      : t("export:incompatibleUnreadable");
  };

  const renderBody = () => {
    if (loading) {
      return (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress size={28} />
        </Box>
      );
    }
    if (error) {
      return <Alert severity="error">{t("export:datasetsLoadError")}</Alert>;
    }
    if (!datasets.length) {
      return (
        <Typography color="text.secondary" sx={{ py: 4 }}>
          {t("export:noDatasets")}
        </Typography>
      );
    }
    return (
      <TableContainer
        sx={{ border: 1, borderColor: "divider", borderRadius: 1 }}
      >
        <Table size="small" aria-label={t("export:selectDatasetTitle")}>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>{t("export:columnName")}</TableCell>
              <TableCell align="right">{t("export:columnRows")}</TableCell>
              <TableCell align="right">{t("export:columnColumns")}</TableCell>
              <TableCell>
                {t("export:columnCompatibility", { platform: platformName })}
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {visibleDatasets.map((dataset) => {
              const disabled = dataset.compatibility.status === "incompatible";
              const isSelected = selected?.id === dataset.id;
              return (
                <TableRow
                  key={dataset.id}
                  hover={!disabled}
                  selected={isSelected}
                  onClick={() => !disabled && onSelect(dataset)}
                  sx={{
                    cursor: disabled ? "not-allowed" : "pointer",
                    opacity: disabled ? 0.55 : 1,
                  }}
                >
                  <TableCell padding="checkbox">
                    <Radio
                      checked={isSelected}
                      disabled={disabled}
                      inputProps={{ "aria-label": dataset.name }}
                      onChange={() => onSelect(dataset)}
                    />
                  </TableCell>
                  <TableCell>{dataset.name}</TableCell>
                  <TableCell align="right">
                    {dataset.total_rows ?? "-"}
                  </TableCell>
                  <TableCell align="right">
                    {dataset.total_columns ?? "-"}
                  </TableCell>
                  <TableCell
                    sx={{ color: STATUS_COLOR[dataset.compatibility.status] }}
                  >
                    {describe(dataset.compatibility)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        px: 4,
        pt: 4,
      }}
    >
      <ExportBreadcrumbs crumbs={[{ label: platformName }]} onBack={onBack} />
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" component="h1">
          {t("export:selectDatasetTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("export:selectDatasetSubtitle", { platform: platformName })}
        </Typography>
      </Box>
      <TextField
        size="small"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder={t("export:searchDatasets")}
        inputProps={{ "aria-label": t("export:searchDatasets") }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        }}
        sx={{ mb: 2, maxWidth: 420 }}
      />
      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pb: 2 }}>
        {renderBody()}
      </Box>
      {!loading && !error && datasets.length > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {t("export:datasetsSummary", {
            count: datasets.length,
            exportable: exportableCount,
            platform: platformName,
          })}
        </Typography>
      )}
      <StepperNavigationFooter
        onBack={onBack}
        onNext={() => onNext(selected)}
        nextDisabled={!selected}
      />
    </Box>
  );
}

ExportDatasetStep.propTypes = {
  platformName: PropTypes.string.isRequired,
  datasets: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      total_rows: PropTypes.number,
      total_columns: PropTypes.number,
      compatibility: PropTypes.shape({
        status: PropTypes.oneOf(["compatible", "warning", "incompatible"])
          .isRequired,
        unsupported_columns: PropTypes.arrayOf(PropTypes.string).isRequired,
      }).isRequired,
    }),
  ).isRequired,
  loading: PropTypes.bool,
  error: PropTypes.bool,
  selected: PropTypes.shape({ id: PropTypes.number }),
  onSelect: PropTypes.func.isRequired,
  onBack: PropTypes.func.isRequired,
  onNext: PropTypes.func.isRequired,
};
