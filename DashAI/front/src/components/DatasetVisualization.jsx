import { useCallback, useState, useEffect } from "react";
import {
  Button,
  Grid,
  Paper,
  Typography,
  CircularProgress,
  Box,
  Chip,
  Alert,
  Divider,
  Tabs,
  Tab,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import {
  AddCircleOutline as AddIcon,
  CheckCircle as CheckIcon,
} from "@mui/icons-material";
import {
  getDatasetFile,
  getDatasetInfo,
  getDatasetFileFiltered,
} from "../api/datasets";
import DatasetTable from "./notebooks/dataset/DatasetTable";
import { getComponents } from "../api/component";
import { useTourContext } from "./tour/TourProvider";
import { useSnackbar } from "notistack";
import JobQueueWidget from "./jobs/JobQueueWidget";
import { getDatasetStatus } from "../utils/datasetStatus";
import { formatDate } from "../pages/results/constants/formatDate";
import Header from "./notebooks/dataset/header/Header";
import Tooltip from "@mui/material/Tooltip";
import OverviewTab from "./notebooks/dataset/tabs/OverviewTab";
import { NumericTab } from "./notebooks/dataset/tabs/NumericTab";
import { CategoricalTab } from "./notebooks/dataset/tabs/CategoricalTab";
import QualityTab from "./notebooks/dataset/tabs/QualityTab";
import CorrelationsTab from "./notebooks/dataset/tabs/CorrelationsTab";
import { QualityAlerts } from "./notebooks/dataset/QualityAlerts";
import { TextTab } from "./notebooks/dataset/tabs/TextTab";

/**
 * Component to visualize dataset information including quality metrics, statistics, and data preview.
 * Can be used across different modules (Notebooks, Models) with customizable action buttons.
 * @param {Object} props
 * @param {Object} props.dataset - Dataset object containing id, name, file_path, status, and created date
 * @param {Function} props.onItemCreated - Callback function when a new item (notebook/session) is created
 * @param {Function} props.onNewItem - Callback function when "New Item" button is clicked
 * @param {string} [props.newItemButtonText="New Item"] - Custom text for the action button (e.g., "New Notebook", "New Session")
 * @param {Array} [props.existingItems=[]] - Array of existing items (notebooks/sessions) for validation
 */
export default function DatasetVisualization({
  dataset,
  onItemCreated,
  onNewItem,
  newItemButtonText = "New Item",
  existingItems = [],
}) {
  const theme = useTheme();

  if (!dataset) {
    return (
      <Box
        sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}
      >
        <CircularProgress sx={{ color: theme.palette.primary.main }} />
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  const [datasetInfo, setDatasetInfo] = useState(null);
  const [tab, setTab] = useState(0);
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();

  useEffect(() => {
    setTab(0);
    const fetchDatasetInfo = async () => {
      if (isProcessing) return;

      try {
        const info = await getDatasetInfo(dataset.id);
        setDatasetInfo(info);
      } catch (error) {
        setDatasetInfo(null);
      }
    };

    fetchDatasetInfo();
  }, [dataset.id, dataset.status]);

  // fetchPage compatible with server-side filtering
  const fetchDatasetPage = useCallback(
    async (page, pageSize, filterModel) => {
      if (isProcessing) return { rows: [], total: 0 };
      try {
        // Use getDatasetFile if no filters, else use getDatasetFileFiltered
        const hasFilters =
          filterModel &&
          Array.isArray(filterModel.items) &&
          filterModel.items.length > 0;
        let data;
        if (hasFilters) {
          data = await getDatasetFileFiltered(
            dataset.file_path,
            page,
            pageSize,
            filterModel,
          );
        } else {
          data = await getDatasetFile(dataset.file_path, page, pageSize);
        }
        return { rows: data.rows ?? [], total: data.total ?? 0 };
      } catch (error) {
        return { rows: [], total: 0 };
      }
    },
    [dataset.file_path, dataset.status, dataset.id],
  );

  const status = getDatasetStatus(dataset.status);
  const isProcessing = !(status === "Finished" || status === "Error");

  return (
    <>
      <Box
        sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 2, mx: 1 }}
      >
        {/* Quick Stats Section */}
        {!isProcessing && datasetInfo && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {/* Dataset quality score */}
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                <Typography variant="h4">{dataset.name}</Typography>
              </Box>
              <Box>
                <Tooltip
                  title="Data Quality Score is calculated based on various factors including missing values, duplicate rows, and data consistency. A higher score indicates better data quality."
                  arrow
                >
                  <Alert
                    severity={
                      datasetInfo?.quality_info?.data_quality_score >= 80
                        ? "success"
                        : datasetInfo?.quality_info?.data_quality_score >= 50
                          ? "warning"
                          : datasetInfo?.quality_info?.data_quality_score
                            ? "error"
                            : "info"
                    }
                    sx={{
                      fontSize: "1rem",
                      height: "45px",
                      display: "flex",
                      alignItems: "center",
                      p: "0 12px",
                    }}
                  >
                    Quality Score:{" "}
                    {datasetInfo?.quality_info?.data_quality_score?.toFixed(
                      2,
                    ) ?? "N/A"}
                    {datasetInfo?.quality_info?.data_quality_score ? "%" : ""}
                  </Alert>
                </Tooltip>
              </Box>
            </Box>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                mb: 1,
                flexWrap: "wrap",
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                }}
              >
                <Typography variant="subtitle1" color="text.secondary">
                  {formatDate(dataset.created)}
                </Typography>
              </Box>

              {/* Buttons */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "flex-end",
                  gap: 2,
                  flexDirection: "column",
                }}
              >
                <Grid
                  sx={{
                    minHeight: "40px",
                    display: "flex",
                    gap: 2,
                    flexWrap: "wrap",
                    justifyContent: "flex-start",
                  }}
                >
                  <Button
                    variant="contained"
                    endIcon={<AddIcon />}
                    disabled={isProcessing}
                    className="new-notebook-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onNewItem) {
                        onNewItem();
                      }
                      if (tourContext && tourContext.run) {
                        setTimeout(() => {
                          tourContext.nextStep();
                        }, 200);
                      }
                    }}
                    sx={{ height: "40px" }}
                  >
                    {newItemButtonText}
                  </Button>
                </Grid>
              </Box>
            </Box>
            <Header
              totalRows={datasetInfo?.total_rows}
              totalColumns={datasetInfo?.total_columns}
              fileSize={datasetInfo?.general_info?.memory_usage_mb}
              duplicateRows={datasetInfo?.general_info?.duplicate_rows}
              missingValues={datasetInfo?.nan}
            />
            {/* Data Quality Alerts */}
            <Box>
              <QualityAlerts
                qualityInfo={datasetInfo?.quality_info}
                generalInfo={datasetInfo?.general_info}
                missingValues={datasetInfo?.nan}
              />
            </Box>
            {/* Tabs */}
            <Tabs
              sx={{
                bgcolor: theme.palette.ui.box,
                borderRadius: 1,
                minHeight: "48px",
                "& .MuiTabs-indicator": {
                  height: "2px",
                },
                "& .MuiTab-root": {
                  minHeight: "48px",
                  fontSize: "0.85rem",
                  borderRadius: "4px",
                  transition: "all 0.2s",
                  border: "1px solid transparent",
                  textTransform: "none",
                  "&:hover": {
                    bgcolor: theme.palette.action.hover,
                  },
                  "&.Mui-disabled": {
                    color: theme.palette.text.disabled,
                    bgcolor: theme.palette.ui.disabled,
                    borderColor: theme.palette.ui.border,
                    opacity: 0.6,
                    cursor: "not-allowed",
                    filter: "grayscale(0.6)",
                    position: "relative",
                    "&::after": {
                      content: '""',
                      position: "absolute",
                      inset: 0,
                      borderRadius: "4px",
                      pointerEvents: "none",
                      background:
                        "repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.1) 10px, rgba(0,0,0,0.1) 20px)",
                    },
                  },
                },
              }}
              value={tab}
              onChange={(_, newValue) => setTab(newValue)}
            >
              <Tab label="Overview" />
              <Tab
                label="Numerical Analysis"
                disabled={
                  !datasetInfo?.numeric_stats ||
                  Object.keys(datasetInfo.numeric_stats).length === 0
                }
              />
              <Tab
                label="Categorical"
                disabled={
                  !datasetInfo?.categorical_stats ||
                  Object.keys(datasetInfo.categorical_stats).length === 0
                }
              />
              <Tab
                label="Text"
                disabled={
                  !datasetInfo?.text_stats ||
                  Object.keys(datasetInfo.text_stats).length === 0
                }
              />
              <Tab label="Data Quality" disabled={!datasetInfo?.quality_info} />
              <Tab
                label="Correlations"
                disabled={
                  !datasetInfo?.correlations ||
                  Object.keys(datasetInfo.correlations).length === 0
                }
              />
            </Tabs>

            {/* Divider */}
            <Divider sx={{ my: 2 }} />

            {/* Content based on selected tab */}
            {tab === 0 && (
              <OverviewTab
                dataset={dataset}
                dtypes={datasetInfo?.general_info?.dtypes}
                nan={datasetInfo?.nan}
                total_rows={datasetInfo?.total_rows}
                fetchDatasetPage={fetchDatasetPage}
              />
            )}
            {tab === 1 && (
              <NumericTab numericStats={datasetInfo?.numeric_stats} />
            )}
            {tab === 2 && (
              <CategoricalTab
                categoricalStats={datasetInfo?.categorical_stats}
              />
            )}
            {tab === 3 && <TextTab textStats={datasetInfo?.text_stats} />}
            {tab === 4 && (
              <QualityTab
                qualityInfo={datasetInfo?.quality_info}
                totalRows={datasetInfo?.total_rows}
              />
            )}
            {tab === 5 && (
              <CorrelationsTab correlations={datasetInfo?.correlations} />
            )}
          </Box>
        )}

        {/* Processing placeholder */}
        {isProcessing && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: 200,
              flexDirection: "column",
              gap: 2,
            }}
          >
            <CircularProgress color="primary" />
            <Typography>Processing your dataset...</Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              textAlign="center"
            >
              This may take a few moments depending on the size of your data.
            </Typography>
          </Box>
        )}
      </Box>

      <JobQueueWidget />
    </>
  );
}
