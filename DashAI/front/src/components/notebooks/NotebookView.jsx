import React, { useState, useEffect } from "react";

import { Box, CircularProgress, Typography } from "@mui/material";
import {
  getExplorersByNotebookId,
  getConvertersByNotebookId,
} from "../../api/notebook";
import ExplorerBox from "./ExplorerBox";
import ConverterBox from "./ConverterBox";

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
  console.log(explorerAndConverters);

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
  }, []);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 3,
        pb: 3,
      }}
    >
      {explorerAndConverters.map((item) =>
        item.type === "explorer" ? (
          <ExplorerBox
            key={item.id}
            explorer={item}
            handleExplorerDetailsClick={() => {}}
          />
        ) : item.type === "converter" ? (
          <ConverterBox key={item.id} converter={item} />
        ) : null,
      )}
    </Box>
  );
}
