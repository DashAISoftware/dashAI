import { useState, useEffect } from "react";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { ViewList, ViewModule } from "@mui/icons-material";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import TransformIcon from "@mui/icons-material/Transform";
import SearchBar from "../threeSectionLayout/SearchBar";
import DescriptionPanel from "./DescriptionPanel";
import ToolList from "./tool/ToolList";
import ToolGrid from "./tool/ToolGrid";
import FormExplorerSection from "./explorerCreation/FormExplorerSection";
import FormConverterSection from "./converterCreation/FormConverterSection";
import { getComponents } from "../../api/component";
import { getDatasetTypesByFilePath } from "../../api/datasets";
import { useSnackbar } from "notistack";
import { useTourContext } from "../tour/TourProvider";
import { useExplorersAndConverters } from "./context/ExplorersAndConvertersContext";
import { ChevronRight } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { useDatasetsAndNotebooks } from "../custom/contexts/DatasetsAndNotebooksContext";
import ColumnInsights from "./dataset/ColumnInsights";

function RightBarDatasetView() {
  const { t } = useTranslation(["datasets"]);
  const { datasetInfo } = useDatasetsAndNotebooks();

  if (!datasetInfo) {
    return (
      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2,
        }}
      >
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", textAlign: "center" }}
        >
          {t("datasets:label.selectNotebookToAccessAnalysisTools")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
      <ColumnInsights
        numericStats={datasetInfo?.numeric_stats}
        textStats={datasetInfo?.text_stats}
      />
    </Box>
  );
}

export default function RightBar({ notebook, onToggle }) {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [converters, setConverters] = useState([]);
  const [explorers, setExplorers] = useState([]);
  const [filteredConverters, setFilteredConverters] = useState([]);
  const [filteredExplorers, setFilteredExplorers] = useState([]);
  const [datasetColumns, setDatasetColumns] = useState([]);
  const tourContext = useTourContext();
  const [viewMode, setViewMode] = useState("list");
  const { enqueueSnackbar } = useSnackbar();
  const { explorersAndConverters } = useExplorersAndConverters();
  const { t } = useTranslation(["datasets", "common"]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getComponents({
          selectTypes: ["Converter", "Explorer"],
        });
        setConverters(data.filter((item) => item.type === "Converter"));
        setExplorers(data.filter((item) => item.type === "Explorer"));
        setFilteredConverters(data.filter((item) => item.type === "Converter"));
        setFilteredExplorers(data.filter((item) => item.type === "Explorer"));
      } catch (error) {
        enqueueSnackbar(t("datasets:error.fetchingExplorersConverters"), {
          variant: "error",
        });
        console.error("Failed to fetch explorers/converters:", error);
      }
    };
    fetchData();
  }, [t]);

  // Fetch dataset columns from notebook file
  useEffect(() => {
    let isMounted = true;
    const fetchAllData = async () => {
      try {
        const types = await getDatasetTypesByFilePath(notebook.file_path);

        if (!isMounted) return;

        const datasetColumns = Object.entries(types).map(
          ([columnName, typeInfo], idx) => ({
            id: idx,
            columnName: columnName,
            valueType: typeInfo.type || t("common:unknown"),
            dataType: typeInfo.dtype || t("common:unknown"),
            order: idx,
          }),
        );

        setDatasetColumns(datasetColumns);
      } catch (error) {
        console.error("Error fetching dataset info/types:", error);
      }
    };

    if (notebook?.file_path) {
      fetchAllData();
    } else {
      setDatasetColumns([]);
    }

    return () => {
      isMounted = false;
    };
  }, [notebook?.file_path, explorersAndConverters]);

  // Validate explorers based on dataset columns
  const validateExplorer = (explorer) => {
    if (!datasetColumns.length) return { disabled: false, tooltip: "" };

    const allowedTypes = explorer?.metadata?.allowed_types || [];
    const allowedDtypes = explorer?.metadata?.allowed_dtypes || [];
    const inputCardinality = explorer?.metadata?.input_cardinality || {};

    let validColumns = datasetColumns;
    let disabled = false;
    let tooltip =
      explorer.description || explorer.metadata?.short_description || "";

    // Filter by allowed semantic types
    if (allowedTypes.length > 0) {
      validColumns = validColumns.filter((col) =>
        allowedTypes.includes(col.valueType),
      );
    }

    // Filter by allowed dtypes
    if (allowedDtypes.length > 0) {
      validColumns = validColumns.filter((col) =>
        allowedDtypes.includes(col.dataType),
      );
    }

    // Check cardinality requirements
    if (inputCardinality.exact != null) {
      if (validColumns.length < inputCardinality.exact) {
        disabled = true;
        if (validColumns.length === 0) {
          tooltip += `\n\n${t("datasets:error.noValidColumnsForExplorer")}`;
        }
        tooltip += `\n\n${t("datasets:error.requiresExactColumns", {
          required: inputCardinality.exact,
          available: validColumns.length,
          count: inputCardinality.exact,
        })}`;
      }
    } else if (inputCardinality.min != null) {
      if (validColumns.length < inputCardinality.min) {
        disabled = true;
        if (validColumns.length === 0) {
          tooltip += `\n\n${t("datasets:error.noValidColumnsForExplorer")}`;
        }
        tooltip += `\n\n${t("datasets:error.requiresMinColumns", {
          required: inputCardinality.min,
          available: validColumns.length,
          count: inputCardinality.min,
        })}`;
      }
    }

    // Check if there are no valid columns and some restriction was applied
    if (
      validColumns.length === 0 &&
      (allowedTypes.length > 0 || allowedDtypes.length > 0)
    ) {
      disabled = true;
      tooltip += `\n\n${t("datasets:error.noValidColumnsWithDtypesMentioned", {
        dtypes: [...allowedTypes, ...allowedDtypes].join(", "),
      })}`;
    }

    return { disabled, tooltip, validColumns };
  };

  // Validate converters based on dataset columns
  const validateConverter = (converter) => {
    if (!datasetColumns.length) return { disabled: false, tooltip: "" };

    const allowedTypes = converter?.metadata?.allowed_types || [];
    const allowedDtypes = converter?.metadata?.allowed_dtypes || [];

    let validColumns = datasetColumns;
    let disabled = false;
    let tooltip =
      converter.description || converter.metadata?.short_description || "";

    // Filter by allowed semantic types
    if (allowedTypes.length > 0) {
      validColumns = validColumns.filter((col) =>
        allowedTypes.includes(col.valueType),
      );
    }

    // Filter by allowed dtypes
    if (allowedDtypes.length > 0) {
      validColumns = validColumns.filter((col) =>
        allowedDtypes.includes(col.dataType),
      );
    }

    // Check if there are no valid columns at all (some restriction was applied)
    if (
      validColumns.length === 0 &&
      (allowedTypes.length > 0 || allowedDtypes.length > 0)
    ) {
      disabled = true;
      tooltip += `\n\n${t("datasets:error.noValidColumnsWithDtypesMentioned", {
        dtypes: [...allowedTypes, ...allowedDtypes].join(", "),
      })}`;
    }

    return { disabled, tooltip, validColumns };
  };

  useEffect(() => {
    const filteredAndValidatedExplorers = explorers
      .filter(
        (item) =>
          item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (item.metadata.short_description
            ? item.metadata.short_description
                .toLowerCase()
                .includes(searchQuery.toLowerCase())
            : item.description
                .toLowerCase()
                .includes(searchQuery.toLowerCase())),
      )
      .map((explorer) => {
        const validation = validateExplorer(explorer);
        return {
          ...explorer,
          disabled: validation.disabled,
          tooltip: validation.tooltip,
          validColumns: validation.validColumns,
          notebook,
        };
      });

    setFilteredExplorers(filteredAndValidatedExplorers);

    const filteredAndValidatedConverters = converters
      .filter(
        (item) =>
          item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (item.metadata.short_description
            ? item.metadata.short_description
                .toLowerCase()
                .includes(searchQuery.toLowerCase())
            : item.description
                .toLowerCase()
                .includes(searchQuery.toLowerCase())),
      )
      .map((converter) => {
        const validation = validateConverter(converter);
        return {
          ...converter,
          disabled: validation.disabled,
          tooltip: validation.tooltip,
          validColumns: validation.validColumns,
          notebook,
        };
      });

    setFilteredConverters(filteredAndValidatedConverters);
  }, [searchQuery, explorers, converters, datasetColumns, notebook]);

  const handleChangeTab = (event, newValue) => {
    setActiveTab(newValue);
    setSearchQuery("");

    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          height: "100%",
          width: "100%",
        }}
        className="right-bar-container"
      >
        <Box
          sx={{
            p: 2,
            borderBottom: `1px solid ${theme.palette.ui.border}`,
            flexShrink: 0,
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6" color="text.primary">
            {t("datasets:label.analysisTools")}
          </Typography>
          <IconButton
            size="small"
            onClick={onToggle}
            sx={{ color: "text.secondary" }}
          >
            <ChevronRight />
          </IconButton>
        </Box>

        {notebook ? (
          <>
            {/* Tabs Section */}
            <Tabs
              value={activeTab}
              onChange={handleChangeTab}
              centered
              sx={{ flexShrink: 0 }}
            >
              <Tab
                data-tour="explorers-tab"
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <AnalyticsIcon sx={{ fontSize: 18 }} />
                    {t("datasets:label.explore")}
                  </Box>
                }
              />
              <Tab
                data-tour="converters-tab"
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <TransformIcon sx={{ fontSize: 18 }} />
                    {t("datasets:label.convert")}
                  </Box>
                }
              />
            </Tabs>

            <Box
              sx={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
              className="explorer-converter-box"
            >
              {/* Search bar */}
              <Box
                sx={{
                  p: 2,
                  borderBottom: `1px solid ${theme.palette.ui.border}`,
                  flexShrink: 0,
                }}
              >
                <SearchBar
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onClear={() => setSearchQuery("")}
                  placeholder={t("datasets:label.searchExplorersConverters")}
                />
              </Box>
              {/* View Mode Toggle */}
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  px: 2,
                  py: 1,
                  borderBottom: `1px solid ${theme.palette.ui.border}`,
                  flexShrink: 0,
                }}
              >
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  {t("datasets:label.viewMode")}
                </Typography>
                <ToggleButtonGroup
                  value={viewMode}
                  exclusive
                  onChange={(_, newMode) => newMode && setViewMode(newMode)}
                  size="small"
                  sx={{
                    "& .MuiToggleButton-root": {
                      color: "text.secondary",
                      border: "1px solid",
                      borderColor: theme.palette.ui.border,
                      "&.Mui-selected": {
                        bgcolor: theme.palette.ui.border,
                        color: theme.palette.accent.main,
                      },
                    },
                  }}
                >
                  <ToggleButton value="list">
                    <ViewList sx={{ fontSize: 18 }} />
                  </ToggleButton>
                  <ToggleButton value="grid">
                    <ViewModule sx={{ fontSize: 18 }} />
                  </ToggleButton>
                </ToggleButtonGroup>
              </Box>

              {/* Tool list and description */}
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  flex: 1,
                  overflow: "hidden",
                  minWidth: 0,
                }}
              >
                {/* Tool list - grid */}
                {viewMode === "list" ? (
                  <Box
                    sx={{
                      flex: 1,
                      overflowY: "auto",
                      overflowX: "hidden",
                      p: 2,
                      minWidth: 0,
                    }}
                  >
                    {activeTab === 0 && (
                      <ToolList
                        tools={filteredExplorers}
                        notebook={notebook}
                        FormComponent={FormExplorerSection}
                      />
                    )}
                    {activeTab === 1 && (
                      <ToolList
                        tools={filteredConverters}
                        notebook={notebook}
                        FormComponent={FormConverterSection}
                      />
                    )}
                  </Box>
                ) : (
                  <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
                    {activeTab === 0 && (
                      <ToolGrid
                        tools={filteredExplorers}
                        notebook={notebook}
                        FormComponent={FormExplorerSection}
                      />
                    )}
                    {activeTab === 1 && (
                      <ToolGrid
                        tools={filteredConverters}
                        notebook={notebook}
                        FormComponent={FormConverterSection}
                      />
                    )}
                  </Box>
                )}

                {/* Description panel - Fixed height */}
                <DescriptionPanel />
              </Box>
            </Box>
          </>
        ) : (
          <RightBarDatasetView />
        )}
      </Box>
    </SideBar>
  );
}
