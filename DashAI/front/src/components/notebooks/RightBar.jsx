import React, { useState } from "react";
import SideBar from "../threeSectionLayout/SideBar";
import { Box, Paper, Typography, Tabs, Tab } from "@mui/material";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import TransformIcon from "@mui/icons-material/Transform";
import SearchBar from "../threeSectionLayout/SearchBar";
import DescriptionPanel from "./DescriptionPanel";
import ExplorerList from "./ExplorerList";
import ConverterList from "./ConverterList";

export default function RightBar({ notebook }) {
  const [activeTab, setActiveTab] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredTool, setHoveredTool] = useState(null);
  const [filteredConverters, setFilteredConverters] = useState([]);
  const [filteredExplorers, setFilteredExplorers] = useState([]);

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
                      handleExplorerClick={() => {}}
                    />
                  )}
                  {activeTab === 1 && (
                    <ConverterList
                      converters={filteredConverters}
                      hoveredTool={hoveredTool}
                      setHoveredTool={setHoveredTool}
                      handleConverterClick={() => {}}
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
