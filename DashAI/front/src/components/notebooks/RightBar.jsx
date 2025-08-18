import React, { useState, useEffect } from "react";
import SideBar from "../threeSectionLayout/SideBar";
import { Box, Paper, Typography, Tabs, Tab } from "@mui/material";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import TransformIcon from "@mui/icons-material/Transform";
import SearchBar from "../threeSectionLayout/SearchBar";
import DescriptionPanel from "./DescriptionPanel";
import ExplorerList from "./ExplorerList";
import ConverterList from "./ConverterList";
import NotebookEditColumnsModal from "./NotebookEditColumnsModal";
import { ExplorersAndConvertersProvider } from "./context/ExplorersAndConvertersContext";
import { getComponents } from "../../api/component";
import { useSnackbar } from "notistack";

export default function RightBar({ notebook }) {
  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredTool, setHoveredTool] = useState(null);
  const [converters, setConverters] = useState([]);
  const [explorers, setExplorers] = useState([]);
  const [filteredConverters, setFilteredConverters] = useState([]);
  const [filteredExplorers, setFilteredExplorers] = useState([]);
  const [editColumnsModalOpen, setEditColumnsModalOpen] = useState(false);
  const [selectedExplorer, setSelectedExplorer] = useState(null);
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

  useEffect(() => {
    setFilteredExplorers(
      explorers.filter((item) =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    );
    setFilteredConverters(
      converters.filter((item) =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    );
  }, [searchQuery]);

  const handleExplorerClick = (explorerData) => {
    console.log("=== Explorer Click Debug ===");
    console.log("Clicked explorer object:", explorerData);
    console.log("Explorer name:", explorerData?.name);
    console.log("Explorer metadata:", explorerData?.metadata);
    console.log("========================");

    setSelectedExplorer(explorerData);
    setEditColumnsModalOpen(true);
  };

  const handleCloseEditColumnsModal = () => {
    setEditColumnsModalOpen(false);
    setSelectedExplorer(null);
  };

  const handleSelectionChange = (selectedColumns) => {
    console.log("=== Selection Change Debug ===");
    console.log("Selected columns:", selectedColumns);
    console.log("Explorer:", selectedExplorer?.name);
    console.log("========================");
    // Here you can add logic to handle the column selection
    // For example, storing it in the notebook state or sending it to the backend
  };

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
                  <ExplorersAndConvertersProvider>
                    {activeTab === 0 && (
                      <ExplorerList
                        explorers={filteredExplorers}
                        hoveredTool={hoveredTool}
                        setHoveredTool={setHoveredTool}
                        handleExplorerClick={handleExplorerClick}
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
                  </ExplorersAndConvertersProvider>
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

      {/* Edit Columns Modal */}
      <NotebookEditColumnsModal
        open={editColumnsModalOpen}
        onClose={handleCloseEditColumnsModal}
        explorerData={selectedExplorer}
        notebook={notebook}
        onSelectionChange={handleSelectionChange}
      />
    </SideBar>
  );
}
