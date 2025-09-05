import { useState, useEffect } from "react";
import SideBar from "../threeSectionLayout/SideBar";
import { Box, Typography, Tabs, Tab } from "@mui/material";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import TransformIcon from "@mui/icons-material/Transform";
import SearchBar from "../threeSectionLayout/SearchBar";
import DescriptionPanel from "./DescriptionPanel";
import ExplorerList from "./explorerCreation/ExplorerList";
import ConverterList from "./converterCreation/ConverterList";
import { getComponents } from "../../api/component";
import { getDatasetTypesByFilePath } from "../../api/datasets";
import { useSnackbar } from "notistack";

export default function RightBar({ notebook }) {
  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredTool, setHoveredTool] = useState(null);
  const [converters, setConverters] = useState([]);
  const [explorers, setExplorers] = useState([]);
  const [filteredConverters, setFilteredConverters] = useState([]);
  const [filteredExplorers, setFilteredExplorers] = useState([]);
  const [datasetColumns, setDatasetColumns] = useState([]);
  const { enqueueSnackbar } = useSnackbar();

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
  }, [notebook?.file_path]);

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

    if (!allowedDtypes.includes("*") && allowedDtypes.length > 0) {
      tooltip += `\n\nAccepts: ${allowedDtypes.join(", ")}`;
    }

    if (restrictedDtypes.length > 0) {
      tooltip += `\n\nRestricted: ${restrictedDtypes.join(", ")}`;
    }

    return { disabled, tooltip, validColumns };
  };

  useEffect(() => {
    const filteredAndValidatedExplorers = explorers
      .filter((item) =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()),
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

    setFilteredConverters(
      converters.filter((item) =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    );
  }, [searchQuery, explorers, converters, datasetColumns, notebook]);

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          height: "100%",
        }}
      >
        <Box sx={{ p: 2, borderBottom: "1px solid #333", flexShrink: 0 }}>
          <Typography variant="h6">Analysis Tools</Typography>
        </Box>

        {notebook ? (
          <>
            {/* Tabs Section */}
            <Tabs
              value={activeTab}
              onChange={(_, newValue) => setActiveTab(newValue)}
              centered
              sx={{ flexShrink: 0 }}
            >
              <Tab
                label={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <AnalyticsIcon sx={{ fontSize: 18 }} />
                    Explore
                  </Box>
                }
              />
              <Tab
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

              {/* Tool list and description */}
              <Box
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  flex: 1,
                  overflow: "hidden",
                }}
              >
                {/* Tool list */}
                <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
                  {activeTab === 0 && (
                    <ExplorerList
                      explorers={filteredExplorers}
                      hoveredTool={hoveredTool}
                      setHoveredTool={setHoveredTool}
                    />
                  )}
                  {activeTab === 1 && (
                    <ConverterList
                      converters={filteredConverters}
                      hoveredTool={hoveredTool}
                      setHoveredTool={setHoveredTool}
                      notebook={notebook}
                    />
                  )}
                </Box>

                {/* Description panel - Fixed height */}
                <DescriptionPanel hoveredTool={hoveredTool} />
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
