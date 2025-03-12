import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { deleteDataset } from "../../api/datasets";
import { useSnackbar } from "notistack";

/**
 * Modal component that displays image columns information after dataset upload
 * @param {boolean} open - Controls if the modal is open
 * @param {function} onClose - Function to handle modal close
 * @param {object} imageColumnsInfo - Object containing image columns information
 * @param {number} datasetId - ID of the dataset
 * @param {function} updateDatasets - Function to update datasets
 */
const ColumnDetailsTable = ({ info }) => (
  <TableContainer component={Paper}>
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Property</TableCell>
          <TableCell>Value</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        <TableRow>
          <TableCell>Image Percentage</TableCell>
          <TableCell>{info.image_percentage.toFixed(2)}%</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Total Paths</TableCell>
          <TableCell>{info.total_paths}</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Valid Paths Count</TableCell>
          <TableCell>{info.valid_paths_count}</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Invalid Paths Count</TableCell>
          <TableCell>{info.invalid_paths_count}</TableCell>
        </TableRow>
        <TableRow>
          <TableCell>Threshold Used</TableCell>
          <TableCell>{(info.threshold_used * 100).toFixed(2)}%</TableCell>
        </TableRow>
      </TableBody>
    </Table>

    {/* Show invalid paths if any exist */}
    {info.invalid_paths.length > 0 && (
      <Box sx={{ mt: 2, p: 2 }}>
        <Typography variant="subtitle2" color="error">
          Invalid Paths:
        </Typography>
        <Paper sx={{ p: 1, maxHeight: 100, overflow: "auto" }}>
          {info.invalid_paths.map((path, index) => (
            <Typography key={index} variant="caption" display="block">
              {path}
            </Typography>
          ))}
        </Paper>
      </Box>
    )}
  </TableContainer>
);

const ImageColumnsInfoModal = ({
  open,
  onClose,
  imageColumnsInfo,
  datasetId,
  updateDatasets,
}) => {
  const { enqueueSnackbar } = useSnackbar();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeleted, setIsDeleted] = useState(false);

  // Separar columnas en imágenes y no imágenes
  const imageColumns = Object.entries(imageColumnsInfo).filter(
    ([_, info]) => info.is_image_column,
  );
  const nonImageColumns = Object.entries(imageColumnsInfo).filter(
    ([_, info]) => !info.is_image_column,
  );

  // Verificar si hay rutas inválidas en columnas de imágenes
  const hasInvalidPaths = imageColumns.some(
    ([_, info]) => info.invalid_paths_count > 0,
  );

  // Efecto para eliminar automáticamente cuando se abre el modal
  useEffect(() => {
    const autoDeleteDataset = async () => {
      if (open && hasInvalidPaths && !isDeleting && !isDeleted) {
        setIsDeleting(true);
        try {
          await deleteDataset(datasetId);
          setIsDeleted(true);
          enqueueSnackbar("Dataset deleted due to invalid image paths", {
            variant: "warning",
            autoHideDuration: 6000,
          });
          updateDatasets();
        } catch (error) {
          console.error("Error deleting dataset:", error);
          enqueueSnackbar("Error while trying to delete the dataset", {
            variant: "error",
          });
        } finally {
          setIsDeleting(false);
        }
      }
    };

    autoDeleteDataset();
  }, [open, hasInvalidPaths, datasetId]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Dataset Image Columns Analysis</DialogTitle>
      <DialogContent>
        {hasInvalidPaths && (
          <Alert severity={"error"} sx={{ mb: 3 }}>
            {isDeleted
              ? "Dataset has been automatically deleted due to invalid image paths. You can close this window and upload a new dataset with valid paths."
              : isDeleting
              ? "Deleting dataset due to invalid image paths..."
              : "Warning: Invalid file paths detected in image columns. The dataset will be automatically deleted as type inference cannot be performed."}
          </Alert>
        )}

        {/* Sección de columnas de imágenes */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Image Columns ({imageColumns.length})
          </Typography>
          {imageColumns.map(([columnName, info]) => (
            <Accordion
              key={columnName}
              sx={{
                mb: 1,
                ...(info.invalid_paths_count > 0 && {
                  "&.MuiPaper-root": {
                    backgroundColor: "rgba(211, 47, 47, 0.04)", // Rojo muy sutil
                    borderLeft: "4px solid #d32f2f", // Borde rojo a la izquierda
                  },
                }),
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>
                  {columnName}
                  {info.invalid_paths_count > 0 && (
                    <Typography
                      component="span"
                      sx={{
                        ml: 2,
                        color: "#d32f2f", // Rojo más oscuro
                        fontWeight: 500,
                      }}
                    >
                      ({info.invalid_paths_count} invalid paths)
                    </Typography>
                  )}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <ColumnDetailsTable info={info} />
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>

        {/* Sección de columnas no-imágenes */}
        <Box>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Non-Image Columns ({nonImageColumns.length})
          </Typography>
          {nonImageColumns.map(([columnName, info]) => (
            <Accordion key={columnName} sx={{ mb: 1 }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>{columnName}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <ColumnDetailsTable info={info} />
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

ImageColumnsInfoModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  imageColumnsInfo: PropTypes.object.isRequired,
  datasetId: PropTypes.number.isRequired,
  updateDatasets: PropTypes.func.isRequired,
};

ColumnDetailsTable.propTypes = {
  info: PropTypes.object.isRequired,
};

export default ImageColumnsInfoModal;
