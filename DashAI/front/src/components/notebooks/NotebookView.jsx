import React, { useState, useEffect, useCallback, useRef } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";
import {
  getExplorersByNotebookId,
  getConvertersByNotebookId,
} from "../../api/notebook";
import ExplorerBox from "./ExplorerBox";
import ConverterBox from "./ConverterBox";
import ExplorerDetailsModal from "./ExplorerDetailsModal";
import { useExplorersAndConverters } from "./context/ExplorersAndConvertersContext";

import { FixedSizeList as List } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";

const RowItem = React.memo(function RowItem({
  item,
  handleExplorerDetailsClick,
  style,
}) {
  return (
    <Box style={style}>
      {item.type === "explorer" ? (
        <ExplorerBox
          explorer={item}
          handleExplorerDetailsClick={handleExplorerDetailsClick}
          height={320}
        />
      ) : item.type === "converter" ? (
        <ConverterBox converter={item} height={320} />
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
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollToItem(explorersAndConverters.length - 1);
    }
  }, [explorersAndConverters]);

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
    <Box sx={{ height: "100%" }}>
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
      ) : (
        <AutoSizer>
          {({ height, width }) => (
            <List
              ref={listRef}
              height={height}
              itemCount={explorersAndConverters.length}
              itemSize={340}
              width={width}
            >
              {({ index, style }) => (
                <RowItem
                  item={explorersAndConverters[index]}
                  handleExplorerDetailsClick={handleExplorerDetailsClick}
                  style={style}
                />
              )}
            </List>
          )}
        </AutoSizer>
      )}

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
