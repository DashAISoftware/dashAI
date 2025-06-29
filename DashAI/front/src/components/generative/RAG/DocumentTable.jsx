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
} from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import DeleteIcon from "@mui/icons-material/Delete";
import { Margin } from "@mui/icons-material";

export default function DocumentTable({
  documents,
  selectedIds,
  onToggle,
  onSelectAll,
  onDeselectAll,
  onRemove,
}) {

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
      {documents.length === 0 ? (
        <Typography variant="body1" color="warning.main" textAlign="center" mt={16} mx={"auto "}>
          No documents available.
        </Typography>
      ) : (
        <>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell />
                <TableCell>Name</TableCell>
                <TableCell>Updated</TableCell>
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
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.includes(doc.id)}
                      onChange={() => onToggle(doc.id)}
                    />
                  </TableCell>
                  <TableCell>{doc.name}</TableCell>
                  <TableCell>{doc.updatedAt}</TableCell>
                  <TableCell align="right">
                    <Box display="flex" flexDirection="row" justifyContent="flex-end">
                      <Tooltip title="Preview">
                        <IconButton size="small">
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
            mb={2}
            alignItems="right"
            justifyContent="flex-end"
            >
            <Button size="small" onClick={onDeselectAll}>Deselect All</Button>
            <Button size="small" onClick={onSelectAll}>Select All</Button>
          </Box>
        </>
      )}
    </Box>
  );
}
