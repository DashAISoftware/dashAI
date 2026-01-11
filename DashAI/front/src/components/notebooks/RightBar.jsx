import { useState, useEffect } from "react";
import SideBar from "../threeSectionLayout/SideBar";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
} from "@mui/material";
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

export default function RightBar({ notebook, onToggle }) {
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
        enqueueSnackbar("Failed to fetch explorers/converters", {
          variant: "error",
        });
        console.error("Failed to fetch explorers/converters:", error);
      }
    };
    fetchData();
  }, []);

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
            valueType: typeInfo.type || "Unknown",
            dataType: typeInfo.dtype || "Unknown",
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

    const allowedDtypes = explorer?.metadata?.allowed_dtypes || ["*"];
    const restrictedDtypes = explorer?.metadata?.restricted_dtypes || [];
    const inputCardinality = explorer?.metadata?.input_cardinality || {};

    let validColumns = datasetColumns;
    let disabled = false;
    let tooltip = explorer.description || "";

    // Filter by allowed dtypes
    if (!allowedDtypes.includes("*")) {
      validColumns = datasetColumns.filter((col) =>
        allowedDtypes.includes(col.dataType),
      );
    }

    // Filter out restricted dtypes
    if (
      restrictedDtypes.some((dtype) =>
        datasetColumns.some((col) => col.dataType === dtype),
      )
    ) {
      validColumns = validColumns.filter(
        (col) => !restrictedDtypes.includes(col.dataType),
      );
    }

    // Check cardinality requirements
    if (inputCardinality.exact != undefined && inputCardinality.exact != null) {
      if (validColumns.length < inputCardinality.exact) {
        disabled = true;
        if (validColumns.length === 0) {
          tooltip += `\n\nThis dataset does not have any valid columns for this explorer.`;
        }
        tooltip += `\n\nRequires exactly ${
          inputCardinality.exact
        } valid column${inputCardinality.exact === 1 ? "" : "s"}, but ${
          validColumns.length
        } available.`;
      }
    } else {
      if (inputCardinality.min != undefined && inputCardinality.min != null) {
        if (validColumns.length < inputCardinality.min) {
          disabled = true;
          if (validColumns.length === 0) {
            tooltip += `\n\nThis dataset does not have any valid columns for this explorer.`;
          }
          tooltip += `\n\nRequires at least ${
            inputCardinality.min
          } valid column${inputCardinality.min === 1 ? "" : "s"}, but only ${
            validColumns.length
          } available.`;
        }
      }
    }

    // Check if there are no valid columns at all
    if (
      validColumns.length === 0 &&
      allowedDtypes.length > 0 &&
      !allowedDtypes.includes("*")
    ) {
      disabled = true;
      tooltip += `\n\nThis dataset does not have any columns with the required data types.`;
    }

    return { disabled, tooltip, validColumns };
  };

  // Validate converters based on dataset columns
  const validateConverter = (converter) => {
    if (!datasetColumns.length) return { disabled: false, tooltip: "" };

    const allowedDtypes = converter?.metadata?.allowed_dtypes || ["*"];
    const restrictedDtypes = converter?.metadata?.restricted_dtypes || [];

    let validColumns = datasetColumns;
    let disabled = false;
    let tooltip =
      converter.description || converter.metadata?.short_description || "";

    // Filter by allowed dtypes
    if (!allowedDtypes.includes("*")) {
      validColumns = datasetColumns.filter((col) =>
        allowedDtypes.includes(col.dataType),
      );
    }

    // Filter out restricted dtypes
    if (
      restrictedDtypes.some((dtype) =>
        datasetColumns.some((col) => col.dataType === dtype),
      )
    ) {
      validColumns = validColumns.filter(
        (col) => !restrictedDtypes.includes(col.dataType),
      );
    }

    // Check if there are no valid columns at all
    if (
      validColumns.length === 0 &&
      allowedDtypes.length > 0 &&
      !allowedDtypes.includes("*")
    ) {
      disabled = true;
      tooltip += `\n\nThis dataset does not have any columns with the required data types (${allowedDtypes.join(
        ", ",
      )}).`;
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
            borderBottom: "1px solid #333",
            flexShrink: 0,
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Typography variant="h6" color="text.primary">
            Analysis Tools
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
                    Explore
                  </Box>
                }
              />
              <Tab
                data-tour="converters-tab"
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <TransformIcon sx={{ fontSize: 18 }} />
                    Convert
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
              <Box sx={{ p: 2, borderBottom: "1px solid #333", flexShrink: 0 }}>
                <SearchBar
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onClear={() => setSearchQuery("")}
                  placeholder="Search explorers/converters"
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
                  borderBottom: "1px solid #333",
                  flexShrink: 0,
                }}
              >
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  View mode
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
                      borderColor: "ui.border",
                      "&.Mui-selected": {
                        bgcolor: "ui.border",
                        color: "accent.main",
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
              Select a notebook to access analysis tools.
            </Typography>
          </Box>
        )}
      </Box>
    </SideBar>
  );
}
