import React, { useState, useEffect, useCallback } from "react";

import { Box, CircularProgress, Typography } from "@mui/material";
import {
  getExplorersByNotebookId,
  getConvertersByNotebookId,
} from "../../api/notebook";
import ExplorerBox from "./ExplorerBox";
import ConverterBox from "./ConverterBox";
import ExplorerDetailsModal from "./ExplorerDetailsModal";

const RowItem = React.memo(
  function RowItem({ item, handleExplorerDetailsClick }) {
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
  },
  // only renders if the item changes
  (prevProps, nextProps) => prevProps.item === nextProps.item,
);

export default function NotebookView({ notebook }) {
  if (!notebook) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100vh",
        }}
      >
        <CircularProgress sx={{ color: "#00BEBB" }} />
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  const [explorerAndConverters, setExplorerAndConverters] = useState([]);
  const [openExplorerDetails, setOpenExplorerDetails] = useState(false);
  const [selectedExplorer, setSelectedExplorer] = useState(null);

  console.log(selectedExplorer);
  console.log(openExplorerDetails);

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
        setExplorerAndConverters(merged);
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

  const Row = useCallback(
    ({ index }) => {
      const item = explorerAndConverters[index];
      return (
        <RowItem
          item={item}
          key={`${item.type}-${index}`}
          handleExplorerDetailsClick={handleExplorerDetailsClick}
        />
      );
    },
    [explorerAndConverters],
  );

  return (
    <>
      {explorerAndConverters.length === 0 ? (
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
        {explorerAndConverters.map((_, idx) =>
          Row({ index: idx }, handleExplorerDetailsClick),
        )}
      </Box>
      <ExplorerDetailsModal
        open={openExplorerDetails}
        onClose={() => {
          setOpenExplorerDetails(false);
          setSelectedExplorer(null);
        }}
        explorer={selectedExplorer}
      />
    </>
  );
}
