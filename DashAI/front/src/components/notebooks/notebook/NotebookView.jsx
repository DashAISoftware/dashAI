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
}) {
  return (
    <Box
      sx={{
        my: 2,
        height: "370px",
      }}
    >
      {item.type === "explorer" ? (
        <ExplorerBox
          explorer={item}
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
  const { t } = useTranslation(["datasets", "common"]);

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

  const { explorersAndConverters, setExplorersAndConverters } =
    useExplorersAndConverters();
  const [openDeleteExplorerConfirmation, setOpenDeleteExplorerConfirmation] =
    useState(false);
  const [openDeleteConverterConfirmation, setOpenDeleteConverterConfirmation] =
    useState(false);
  const [explorerToDelete, setExplorerToDelete] = useState(null);
  const [converterToDelete, setConverterToDelete] = useState(null);
  const [deleteModalContent, setDeleteModalContent] = useState("");
  const [itemsToDelete, setItemsToDelete] = useState([]);
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
