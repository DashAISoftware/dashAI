import React, { useState, useEffect } from "react";
import SideBar from "../threeSectionLayout/SideBar";
import { Box, Paper, Typography, Tabs, Tab } from "@mui/material";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import TransformIcon from "@mui/icons-material/Transform";
import SearchBar from "../threeSectionLayout/SearchBar";
import DescriptionPanel from "./DescriptionPanel";
import ExplorerList from "./ExplorerList";
import ConverterList from "./ConverterList";
import { getComponents } from "../../api/component";
import { getDatasetFile } from "../../api/datasets";
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
      const data = await getComponents({
        selectTypes: ["Converter", "Explorer"],
      });
      setConverters(data.filter((item) => item.type === "Converter"));
      setExplorers(data.filter((item) => item.type === "Explorer"));
      setFilteredConverters(data.filter((item) => item.type === "Converter"));
      setFilteredExplorers(data.filter((item) => item.type === "Explorer"));
    };
    try {
      fetchData();
    } catch (error) {
      enqueueSnackbar("Failed to fetch explorers/converters", {
        variant: "error",
      });
      console.error("Failed to fetch explorers/converters:", error);
    }
  }, []);

  // Fetch dataset columns from notebook file
  useEffect(() => {
    const fetchDatasetColumns = async () => {
      if (notebook?.file_path) {
        try {
          // Get a small sample to extract column info
          const datasetFile = await getDatasetFile(notebook.file_path, 0, 1);

          if (datasetFile.rows && datasetFile.rows.length > 0) {
            const firstRow = datasetFile.rows[0];
            const columnNames = Object.keys(firstRow);

            const cols = columnNames.map((columnName, index) => {
              const value = firstRow[columnName];
              let dataType = "unknown";

              // Infer types from the sample data
              if (typeof value === "number") {
                dataType = Number.isInteger(value) ? "int64" : "float64";
              } else if (typeof value === "string") {
                dataType = "object";
              } else if (typeof value === "boolean") {
                dataType = "bool";
              }

              return {
                id: index,
                columnName: columnName,
                dataType: dataType,
              };
            });
            setDatasetColumns(cols);
          }
        } catch (error) {
          console.error("Error fetching dataset columns:", error);
        }
      }
    };

    fetchDatasetColumns();
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
        } valid column${inputCardinality.exact === 1 ? "" : "s"}, but only ${
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

    if (!allowedDtypes.includes("*")) {
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
