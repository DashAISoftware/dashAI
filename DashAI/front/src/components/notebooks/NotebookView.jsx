import React, { useState, useEffect, useCallback } from "react";

import { Box, CircularProgress, Typography } from "@mui/material";
import {
  getExplorersByNotebookId,
  getConvertersByNotebookId,
} from "../../api/notebook";
import ExplorerBox from "./ExplorerBox";
import ConverterBox from "./ConverterBox";
import ExplorerDetailsModal from "./ExplorerDetailsModal";
import { useExplorersAndConverters } from "./context/ExplorersAndConvertersContext";

const RowItem = React.memo(function RowItem({
  item,
  handleExplorerDetailsClick,
}) {
  return (
    <Box>
      {item.type === "explorer" ? (
        <ExplorerBox
          explorer={item}
          handleExplorerDetailsClick={handleExplorerDetailsClick}
        />
      ) : item.type === "converter" ? (
        <ConverterBox converter={item} />
      ) : null}
    </Box>
  );
});

export default function NotebookView({ notebook }) {
  if (!notebook) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <CircularProgress sx={{ color: "#00BEBB" }} />
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  const { explorersAndConverters, setExplorersAndConverters } =
    useExplorersAndConverters();
  const [openExplorerDetails, setOpenExplorerDetails] = useState(false);
  const [selectedExplorer, setSelectedExplorer] = useState(null);

  useEffect(() => {
    const fetchExplorersAndConverters = async () => {
      try {
        const [explorersData, convertersData] = await Promise.all([
          getExplorersByNotebookId(notebook.id),
          getConvertersByNotebookId(notebook.id),
        ]);
        const explorersWithType = explorersData.map((item) => ({
          ...item,
          type: "explorer",
        }));
        const convertersWithType = convertersData.map((item) => ({
          ...item,
          type: "converter",
        }));
        const merged = [...explorersWithType, ...convertersWithType].sort(
          (a, b) => new Date(a.created) - new Date(b.created),
        );
        setExplorersAndConverters(merged);
      } catch (error) {
        console.error("Failed to fetch explorers and converters:", error);
      }
    };

    fetchExplorersAndConverters();
  }, [notebook]);

  const handleExplorerDetailsClick = useCallback((explorer) => {
    setSelectedExplorer(explorer);
    setOpenExplorerDetails(true);
  }, []);

  return (
    <Box>
      {explorersAndConverters.length === 0 ? (
        <Box
          sx={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Typography>
            Start exploring by adding your first explorer or converter!
          </Typography>
        </Box>
      ) : null}
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: 3,
          pb: 3,
        }}
      >
        {explorersAndConverters.map((item, idx) => (
          <RowItem
            item={item}
            key={`${item.type}-${item.id ?? idx}`}
            handleExplorerDetailsClick={handleExplorerDetailsClick}
          />
        ))}
      </Box>
      <ExplorerDetailsModal
        open={openExplorerDetails}
        onClose={() => {
          setOpenExplorerDetails(false);
          setSelectedExplorer(null);
        }}
        explorer={selectedExplorer}
      />
    </Box>
  );
}
