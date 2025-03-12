import React from "react";
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
} from "@mui/material";

/**
 * Modal component that displays image columns information after dataset upload
 * @param {boolean} open - Controls if the modal is open
 * @param {function} onClose - Function to handle modal close
 * @param {object} imageColumnsInfo - Object containing image columns information
 */
const ImageColumnsInfoModal = ({ open, onClose, imageColumnsInfo }) => {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Dataset Image Columns Analysis</DialogTitle>
      <DialogContent>
        {Object.entries(imageColumnsInfo).map(([columnName, info]) => (
          <Box key={columnName} sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Column: {columnName}
            </Typography>
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
                    <TableCell>Is Image Column</TableCell>
                    <TableCell>{info.is_image_column ? "Yes" : "No"}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Image Percentage</TableCell>
                    <TableCell>
                      {(info.image_percentage * 100).toFixed(2)}%
                    </TableCell>
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
                    <TableCell>
                      {(info.threshold_used * 100).toFixed(2)}%
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>

            {/* Show invalid paths if any exist */}
            {info.invalid_paths.length > 0 && (
              <Box sx={{ mt: 2 }}>
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
          </Box>
        ))}
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
};

export default ImageColumnsInfoModal;
