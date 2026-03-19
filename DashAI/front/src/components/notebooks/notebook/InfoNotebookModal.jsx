import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Modal from "@mui/material/Modal";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import CloseIcon from "@mui/icons-material/Close";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableRow from "@mui/material/TableRow";
import { formatDate } from "../../../utils";
import { useTranslation } from "react-i18next";

const EMPTY_ARRAY = [];

export default function InfoNotebookModal({
  notebookData,
  datasets = EMPTY_ARRAY,
  open,
  onClose,
}) {
  const { t } = useTranslation(["datasets", "common"]);

  // Find the associated dataset name
  const getDatasetName = () => {
    if (!notebookData.dataset_id || !datasets.length) {
      return t("common:unknown");
    }
    const dataset = datasets.find((d) => d.id === notebookData.dataset_id);
    return dataset ? dataset.name : t("common:datasetNotFound");
  };

  // If no notebook data is provided, don't render anything
  if (!notebookData) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="notebook-info-modal"
      aria-describedby="notebook-information-details"
    >
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: { xs: "90%", sm: 500 },
          bgcolor: "background.paper",
          borderRadius: 2,
          boxShadow: 12,
          p: 0,
          outline: "none",
        }}
      >
        {/* Modal Header */}
        <Box
          sx={{
            p: 2,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <Box>
            <Typography variant="h6" component="h2">
              {t("datasets:label.notebookInformation")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {notebookData.name}
            </Typography>
          </Box>
          <IconButton
            onClick={onClose}
            size="small"
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        <Box sx={{ p: 3 }}>
          {/* Description Section - Only show if description exists */}
          {notebookData.description && notebookData.description.trim() && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                {t("common:description")}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {notebookData.description}
              </Typography>
            </Box>
          )}

          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("common:metadata")}
          </Typography>
          <TableContainer component={Paper} sx={{ bgcolor: "rgba(0,0,0,0.2)" }}>
            <Table size="small">
              <TableBody>
                <TableRow>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ color: "text.secondary" }}
                  >
                    {t("common:id")}
                  </TableCell>
                  <TableCell align="right">{notebookData.id}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ color: "text.secondary" }}
                  >
                    {t("datasets:label.associatedDataset")}
                  </TableCell>
                  <TableCell align="right">{getDatasetName()}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ color: "text.secondary" }}
                  >
                    {t("common:created")}
                  </TableCell>
                  <TableCell align="right">
                    {formatDate(notebookData.created)}
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ color: "text.secondary" }}
                  >
                    {t("common:lastModified")}
                  </TableCell>
                  <TableCell align="right">
                    {formatDate(notebookData.last_modified)}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      </Box>
    </Modal>
  );
}
