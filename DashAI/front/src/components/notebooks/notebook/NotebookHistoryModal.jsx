import { useState, useCallback } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import ConverterHistoryList from "../converter/ConverterHistoryList";
import DeleteConfirmationModal from "../../threeSectionLayout/DeleteConfirmationModal";
import ItemsToDeleteList from "../converter/ItemsToDeleteList";
import { deleteConverterById } from "../../../api/converter";
import {
  getConvertersByNotebookId,
  getExplorersByNotebookId,
} from "../../../api/notebook";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import { useTranslation } from "react-i18next";

export function NotebookHistoryModal({ open, onClose, notebook, converters }) {
  const { explorersAndConverters, setExplorersAndConverters } =
    useExplorersAndConverters();
  const [openDeleteConverterConfirmation, setOpenDeleteConverterConfirmation] =
    useState(false);
  const [converterToDelete, setConverterToDelete] = useState(null);
  const [deleteModalContent, setDeleteModalContent] = useState("");
  const [itemsToDelete, setItemsToDelete] = useState([]);
  const { t } = useTranslation(["datasets", "common"]);

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

  const handleConfirmConverterDelete = useCallback(async () => {
    if (converterToDelete && notebook) {
      try {
        await deleteConverterById(converterToDelete.id);

        await fetchExplorersAndConverters();

        setOpenDeleteConverterConfirmation(false);
        setConverterToDelete(null);
        setDeleteModalContent("");
        setItemsToDelete([]);
      } catch (error) {
        console.error("Failed to delete converter:", error);
      }
    }
  }, [converterToDelete, notebook, fetchExplorersAndConverters]);

  const handleCancelDelete = useCallback(() => {
    setOpenDeleteConverterConfirmation(false);
    setConverterToDelete(null);
    setDeleteModalContent("");
    setItemsToDelete([]);
  }, []);

  if (!notebook) return null;

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          {t("datasets:label.notebookHistory", { notebook: notebook.name })}
          <IconButton
            onClick={onClose}
            sx={{ position: "absolute", right: 8, top: 8 }}
          >
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 1 }}>
            {converters.length === 0 ? (
              <Typography
                variant="body2"
                color="text.secondary"
                textAlign="center"
                sx={{ py: 4 }}
              >
                {t("datasets:label.noTransformationsAppliedYet")}
              </Typography>
            ) : (
              <ConverterHistoryList
                converters={converters}
                onConverterDelete={handleConverterDeleteClick}
                showDeleteButtons={true}
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t("common:close")}</Button>
        </DialogActions>
      </Dialog>

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
    </>
  );
}
