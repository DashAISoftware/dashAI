import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Modal from "@mui/material/Modal";
import Paper from "@mui/material/Paper";
import CloseIcon from "@mui/icons-material/Close";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableRow from "@mui/material/TableRow";
import { formatDate } from "../../utils";
import { useTranslation } from "react-i18next";

export default function InfoSessionModal({
  sessionData,
  datasets = [],
  tasks = [],
  open,
  onClose,
}) {
  const { t } = useTranslation(["common"]);

  // Find the associated dataset name
  const getDatasetName = () => {
    if (!sessionData.dataset_id || !datasets.length) {
      return t("common:unknown");
    }
    const dataset = datasets.find((d) => d.id === sessionData.dataset_id);
    return dataset ? dataset.name : t("common:datasetNotFound");
  };

  // Get task display name
  const getTaskDisplayName = () => {
    if (!sessionData.task_name) return t("common:unknown");
    const task = tasks.find((t) => t.name === sessionData.task_name);
    return (
      task?.metadata?.display_name ||
      sessionData.task_name
        .replace("Task", "")
        .replace(/([A-Z])/g, " $1")
        .trim()
    );
  };

  // If no session data is provided, don't render anything
  if (!sessionData) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="session-info-modal"
      aria-describedby="session-information-details"
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
              {t("common:sessionInformation")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {sessionData.name}
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

        <Box sx={{ p: 6 }}>
          {/* Description Section - Only show if description exists */}
          {sessionData.description && sessionData.description.trim() && (
            <Box sx={{ mb: 6 }}>
              <Typography variant="subtitle2" sx={{ mb: 2 }}>
                {t("common:description")}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
                {sessionData.description}
              </Typography>
            </Box>
          )}

          <Typography variant="subtitle2" sx={{ mb: 2 }}>
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
                  <TableCell align="right">{sessionData.id}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ color: "text.secondary" }}
                  >
                    {t("common:task")}
                  </TableCell>
                  <TableCell align="right">{getTaskDisplayName()}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ color: "text.secondary" }}
                  >
                    {t("common:associatedDataset")}
                  </TableCell>
                  <TableCell align="right">{getDatasetName()}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell
                    component="th"
                    scope="row"
                    sx={{ color: "text.secondary" }}
                  >
                    {t("common:createdAt")}
                  </TableCell>
                  <TableCell align="right">
                    {formatDate(sessionData.created)}
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
                    {formatDate(sessionData.last_modified)}
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
