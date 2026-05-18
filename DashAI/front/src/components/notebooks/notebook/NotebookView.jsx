import { useTourContext } from "../../tour/TourProvider";
import React, { useState, useEffect, useCallback, useRef } from "react";
import { Virtuoso } from "react-virtuoso";
import { Box, CircularProgress, Typography } from "@mui/material";
import {
  getExplorersByNotebookId,
  getConvertersByNotebookId,
} from "../../../api/notebook";
import ExplorerBox from "../explorer/ExplorerBox";
import ConverterBox from "../converter/ConverterBox";
import DeleteConfirmationModal from "../../threeSectionLayout/DeleteConfirmationModal";
import ItemsToDeleteList from "../converter/ItemsToDeleteList";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { deleteExplorer } from "../../../api/explorer";
import { deleteConverterById } from "../../../api/converter";
import { startJobPolling } from "../../../utils/jobPoller";
import { useTranslation } from "react-i18next";

const RowItem = React.memo(function RowItem({
  item,
  handleExplorerDeleteClick,
  handleConverterDeleteClick,
  handleStatusChange,
  isHighlighted,
}) {
  return (
    <Box
      sx={{
        my: 2,
        p: 1.5,
        height: "394px",
      }}
    >
      {item.type === "explorer" ? (
        <ExplorerBox
          explorer={item}
          handleExplorerDeleteClick={handleExplorerDeleteClick}
          onStatusChange={(id, newStatus) =>
            handleStatusChange(id, newStatus, "explorer")
          }
          isHighlighted={isHighlighted}
        />
      ) : item.type === "converter" ? (
        <ConverterBox
          converter={item}
          handleConverterDeleteClick={handleConverterDeleteClick}
          onStatusChange={(id, newStatus) =>
            handleStatusChange(id, newStatus, "converter")
          }
          isHighlighted={isHighlighted}
        />
      ) : null}
    </Box>
  );
});

export default function NotebookView({ notebook }) {
  const { t } = useTranslation(["datasets", "common"]);
  const tourContext = useTourContext();

  useEffect(() => {
    if (sessionStorage.getItem("startNotebookTour") === "true") {
      sessionStorage.removeItem("startNotebookTour");
      setTimeout(() => {
        if (tourContext && typeof tourContext.startTour === "function") {
          tourContext.startTour();
        } else if (tourContext && typeof tourContext.run === "undefined") {
          tourContext.run = true;
        }
      }, 1000);
    }
  }, [tourContext]);

  const {
    explorersAndConverters,
    setExplorersAndConverters,
    lastAddedItemId,
    setLastAddedItemId,
  } = useExplorersAndConverters();
  const [highlightedItemId, setHighlightedItemId] = useState(null);
  const explorersAndConvertersRef = useRef(explorersAndConverters);
  const [openDeleteExplorerConfirmation, setOpenDeleteExplorerConfirmation] =
    useState(false);
  const [openDeleteConverterConfirmation, setOpenDeleteConverterConfirmation] =
    useState(false);
  const [explorerToDelete, setExplorerToDelete] = useState(null);
  const [converterToDelete, setConverterToDelete] = useState(null);
  const [deleteModalContent, setDeleteModalContent] = useState("");
  const [itemsToDelete, setItemsToDelete] = useState([]);
  const [listSize] = useState(explorersAndConverters.length);
  const listBoxRef = useRef(null);

  const fetchExplorersAndConverters = useCallback(async () => {
    if (!notebook?.id) return;
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
  }, [notebook?.id, setExplorersAndConverters]);

  const getItemsToDelete = useCallback(
    (converterToDelete) => {
      const converterIndex = explorersAndConverters.findIndex(
        (item) => item.id === converterToDelete.id && item.type === "converter",
      );

      if (converterIndex === -1) return [];

      return explorersAndConverters.slice(converterIndex);
    },
    [explorersAndConverters],
  );

  useEffect(() => {
    fetchExplorersAndConverters();
  }, [fetchExplorersAndConverters]);

  const handleExplorerDeleteClick = useCallback((explorer) => {
    setExplorerToDelete(explorer);
    setDeleteModalContent(
      t("datasets:label.deleteExplorerConfirmation", {
        explorer: explorer?.exploration_type,
      }),
    );
    setOpenDeleteExplorerConfirmation(true);
  }, []);

  const handleConverterDeleteClick = useCallback(
    (converter) => {
      setConverterToDelete(converter);

      const items = getItemsToDelete(converter);
      setItemsToDelete(items);

      setDeleteModalContent(
        t("datasets:label.deleteConverterConfirmation", {
          converter: converter?.converter,
        }),
      );

      setOpenDeleteConverterConfirmation(true);
    },
    [getItemsToDelete],
  );

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
    if (!converterToDelete) return;
    try {
      const jobId = await deleteConverterById(converterToDelete.id);
      setOpenDeleteConverterConfirmation(false);
      setConverterToDelete(null);
      setDeleteModalContent("");
      setItemsToDelete([]);
      if (jobId) {
        startJobPolling(
          jobId,
          () => fetchExplorersAndConverters(),
          () => fetchExplorersAndConverters(),
        );
      } else {
        fetchExplorersAndConverters();
      }
    } catch (error) {
      console.error("Failed to delete converter:", error);
    }
  }, [converterToDelete, fetchExplorersAndConverters]);

  const handleCancelDelete = useCallback(() => {
    setOpenDeleteExplorerConfirmation(false);
    setOpenDeleteConverterConfirmation(false);
    setExplorerToDelete(null);
    setConverterToDelete(null);
    setItemsToDelete([]);
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

  useEffect(() => {
    explorersAndConvertersRef.current = explorersAndConverters;
  }, [explorersAndConverters]);

  useEffect(() => {
    if (!lastAddedItemId) return;
    const scrollTimer = setTimeout(() => {
      const list = explorersAndConvertersRef.current;
      const index = list.findIndex(
        (item) =>
          item.id === lastAddedItemId.id && item.type === lastAddedItemId.type,
      );
      const targetIndex = index >= 0 ? index : list.length - 1;
      if (listBoxRef.current && targetIndex >= 0) {
        listBoxRef.current.scrollToIndex({
          index: targetIndex,
          align: "center",
          behavior: "smooth",
        });
      }
      setHighlightedItemId(lastAddedItemId);
      setLastAddedItemId(null);
    }, 100);
    const clearTimer = setTimeout(() => setHighlightedItemId(null), 4100);
    return () => {
      clearTimeout(scrollTimer);
      clearTimeout(clearTimer);
    };
  }, [lastAddedItemId]);

  if (!notebook) {
    return (
      <Box
        sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}
      >
        <CircularProgress color="primary" />
        <Typography>{t("common:loading")}</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        className: "explorer-converter-box",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "auto",
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
          <Typography>{t("datasets:label.noExplorersOrConverters")}</Typography>
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
              handleExplorerDeleteClick={handleExplorerDeleteClick}
              handleConverterDeleteClick={handleConverterDeleteClick}
              handleStatusChange={handleStatusChange}
              isHighlighted={
                highlightedItemId?.id === item.id &&
                highlightedItemId?.type === item.type
              }
            />
          )}
        />
      )}

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
        content={
          <Box>
            <Typography>{deleteModalContent}</Typography>
            <ItemsToDeleteList items={itemsToDelete} />
          </Box>
        }
      />
    </Box>
  );
}
