import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Checkbox,
  Typography,
  IconButton,
  Tooltip,
  Button,
  CircularProgress,
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import DeleteIcon from "@mui/icons-material/Delete";
import PropTypes from "prop-types";

export default function DocumentTable({
  documents,
  selectedIds,
  onToggle,
  onSelectAll,
  onDeselectAll,
  onRemove,
  isLoading = false,
}) {
  // Format the date to a more readable format
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch (e) {
      return dateString;
    }
  };

  return (
    <Box
      sx={{
        backgroundColor: "background.paper",
        borderRadius: 2,
        p: 2,
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}>
      {isLoading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="100%">
          <CircularProgress />
        </Box>
      ) : documents.length === 0 ? (
        <Typography variant="body1" color="warning.main" textAlign="center" mt={16} mx={"auto "}>
          No documents available.
        </Typography>
      ) : (
        <>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={selectedIds.length > 0 && selectedIds.length < documents.length}
                    checked={selectedIds.length === documents.length && documents.length > 0}
                    onChange={(event) => {
                      if (event.target.checked) {
                        onSelectAll();
                      } else {
                        onDeselectAll();
                      }
                    }}
                  />
                </TableCell>
                <TableCell>Id</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Added On</TableCell>
                <TableCell>Last Modified</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {documents.map((doc) => (
                <TableRow
                  key={doc.id}
                  selected={selectedIds.includes(doc.id)}
                  sx={{
                    transition: "background-color 0.3s",
                    backgroundColor: selectedIds.includes(doc.id) ? "action.hover" : "inherit",
                  }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedIds.includes(doc.id)}
                      onChange={() => onToggle(doc.id)}
                    />
                  </TableCell>
                  <TableCell>{doc.id}</TableCell>
                  <TableCell>{doc.file_name}</TableCell>
                  <TableCell>{formatDate(doc.created)}</TableCell>
                  <TableCell>{doc.optional_metadata?.last_modified ? formatDate(doc.optional_metadata.last_modified) : "N/A"}</TableCell>
                  <TableCell align="right">
                    <Box display="flex" flexDirection="row" justifyContent="flex-end">
                      <Tooltip title="Preview">
                        <IconButton size="small" onClick={() => {
                          if (doc.preview) window.open(doc.preview, '_blank');
                          else console.warn("No preview URL available for this document.");
                        }}>
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Remove">
                        <IconButton size="small" onClick={() => onRemove(doc.id)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <Box
            display="flex"
            mb={0}
            mt="auto"
            alignItems="center"
            justifyContent="flex-end"
            gap={1}
            p={1}
            borderTop="1px solid #e0e0e0"
          >
            <Button size="small" onClick={onDeselectAll}>Deselect All</Button>
            <Button size="small" onClick={onSelectAll}>Select All</Button>
          </Box>
        </>
      )}
    </Box>
  );
}

DocumentTable.propTypes = {
  documents: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    createdAt: PropTypes.string.isRequired,
    preview: PropTypes.string,
  })).isRequired,
  selectedIds: PropTypes.arrayOf(PropTypes.string).isRequired,
  onToggle: PropTypes.func.isRequired,
  onSelectAll: PropTypes.func.isRequired,
  onDeselectAll: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
};
