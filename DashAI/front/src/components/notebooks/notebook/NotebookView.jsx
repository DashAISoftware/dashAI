import React, { useState, useEffect, useCallback, useRef } from "react";
import { Virtuoso } from "react-virtuoso";
import { Box, CircularProgress, Typography } from "@mui/material";
import {
  getExplorersByNotebookId,
  getConvertersByNotebookId,
} from "../../../api/notebook";
import ExplorerBox from "../explorer/ExplorerBox";
import ConverterBox from "../converter/ConverterBox";
import ExplorerDetailsModal from "../explorer/ExplorerDetailsModal";
import DeleteConfirmationModal from "../../threeSectionLayout/DeleteConfirmationModal";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { deleteExplorer } from "../../../api/explorer";
import { deleteConverterById } from "../../../api/converter";

const RowItem = React.memo(function RowItem({
  item,
  handleExplorerDetailsClick,
  handleExplorerDeleteClick,
  handleConverterDeleteClick,
  handleStatusChange,
}) {
  return (
    <Box
      sx={{
        my: 2,
      }}
    >
      {item.type === "explorer" ? (
        <ExplorerBox
          explorer={item}
          handleExplorerDetailsClick={handleExplorerDetailsClick}
          handleExplorerDeleteClick={handleExplorerDeleteClick}
          onStatusChange={(id, newStatus) =>
            handleStatusChange(id, newStatus, "explorer")
          }
        />
      ) : item.type === "converter" ? (
        <ConverterBox
          converter={item}
          handleConverterDeleteClick={handleConverterDeleteClick}
          onStatusChange={(id, newStatus) =>
            handleStatusChange(id, newStatus, "converter")
          }
        />
      ) : null}
    </Box>
  );
});

export default function NotebookView({ notebook }) {
  if (!notebook) {
    return (
      <Box
        sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}
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
  const [openDeleteExplorerConfirmation, setOpenDeleteExplorerConfirmation] =
    useState(false);
  const [openDeleteConverterConfirmation, setOpenDeleteConverterConfirmation] =
    useState(false);
  const [explorerToDelete, setExplorerToDelete] = useState(null);
  const [converterToDelete, setConverterToDelete] = useState(null);
  const [deleteModalContent, setDeleteModalContent] = useState("");
  const [listSize, setListSize] = useState(explorersAndConverters.length);
  const listBoxRef = useRef(null);

  const fetchExplorersAndConverters = useCallback(async () => {
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
  }, [notebook.id, setExplorersAndConverters]);

  useEffect(() => {
    fetchExplorersAndConverters();
  }, [fetchExplorersAndConverters]);

  const handleExplorerDetailsClick = useCallback((explorer) => {
    setSelectedExplorer(explorer);
    setOpenExplorerDetails(true);
  }, []);

  const handleExplorerDeleteClick = useCallback((explorer) => {
    setExplorerToDelete(explorer);
    setDeleteModalContent(
      `Are you sure you want to delete the explorer "${explorer?.exploration_type}"? This action cannot be undone.`,
    );
    setOpenDeleteExplorerConfirmation(true);
  }, []);

  const handleConverterDeleteClick = useCallback((converter) => {
    setConverterToDelete(converter);
    setDeleteModalContent(
      `Are you sure you want to delete the converter "${converter?.converter}"? Deleting this converter will also remove all subsequent converters and explorers applied after it. This action cannot be undone.`,
    );
    setOpenDeleteConverterConfirmation(true);
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (explorerToDelete) {
      try {
        await deleteExplorer(explorerToDelete.id);
        setExplorersAndConverters((prev) =>
          prev.filter(
            (item) =>
              !(item.id === explorerToDelete.id && item.type === "explorer"),
          ),
        );

        setOpenDeleteExplorerConfirmation(false);
        setExplorerToDelete(null);
        setDeleteModalContent("");
      } catch (error) {
        console.error("Failed to delete explorer:", error);
      }
    }
  }, [explorerToDelete, setExplorersAndConverters]);

  const handleConfirmConverterDelete = useCallback(async () => {
    if (converterToDelete) {
      try {
        await deleteConverterById(converterToDelete.id);

        await fetchExplorersAndConverters();

        setOpenDeleteConverterConfirmation(false);
        setConverterToDelete(null);
        setDeleteModalContent("");
      } catch (error) {
        console.error("Failed to delete converter:", error);
      }
    }
  }, [converterToDelete, setExplorersAndConverters]);

  const handleCancelDelete = useCallback(() => {
    setOpenDeleteExplorerConfirmation(false);
    setOpenDeleteConverterConfirmation(false);
  }, []);

  const handleStatusChange = useCallback((id, newStatus, type) => {
    setExplorersAndConverters((prev) =>
      prev.map((item) =>
        item.id === id && item.type === type
          ? { ...item, status: newStatus }
          : item,
      ),
    );
  });

  const scrollToBottom = () => {
    if (!listBoxRef.current || explorersAndConverters.length === 0) return;

    listBoxRef.current.scrollToIndex({
      index: listSize - 1,
      align: "start",
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [listSize]);

  useEffect(() => {
    setListSize(explorersAndConverters.length);
  }, [explorersAndConverters]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
      }}
    >
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
        <Virtuoso
          ref={listBoxRef}
          style={{ height: "100%" }}
          initialTopMostItemIndex={listSize > 1 ? listSize - 1 : 0}
          data={explorersAndConverters}
          itemContent={(index, item) => (
            <RowItem
              item={item}
              handleExplorerDetailsClick={handleExplorerDetailsClick}
              handleExplorerDeleteClick={handleExplorerDeleteClick}
              handleConverterDeleteClick={handleConverterDeleteClick}
              handleStatusChange={handleStatusChange}
            />
          )}
        />
      )}
      <ExplorerDetailsModal
        open={openExplorerDetails}
        onClose={() => {
          setOpenExplorerDetails(false);
          setSelectedExplorer(null);
        }}
        explorer={selectedExplorer}
      />
      <DeleteConfirmationModal
        open={openDeleteExplorerConfirmation}
        onClose={handleCancelDelete}
        onConfirm={handleConfirmDelete}
        content={deleteModalContent}
      />
      <DeleteConfirmationModal
        open={openDeleteConverterConfirmation}
        onClose={handleCancelDelete}
        onConfirm={handleConfirmConverterDelete}
        content={deleteModalContent}
      />
    </Box>
  );
}
