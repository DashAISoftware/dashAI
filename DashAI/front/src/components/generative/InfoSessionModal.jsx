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
import { formatDate } from "../../utils";
import { useTranslation } from "react-i18next";

export default function InfoSessionModal({ sessionData, open, onClose }) {
  // If no session data is provided, don't render anything
  if (!sessionData) return null;

  const { t } = useTranslation(["generative", "common"]);

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
              {t("generative:label.sessionInformation")}
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

        {/* Modal Content */}
        <Box sx={{ p: 3 }}>
          <Box sx={{ mb: 3 }}>
            <Chip
              label={sessionData.task_name}
              color="primary"
              size="small"
              sx={{ mb: 1 }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {t("common:model")}:{" "}
              <span style={{ color: "#fff" }}>{sessionData.model_name}</span>
            </Typography>
          </Box>

          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("common:parameters")}:{" "}
          </Typography>
          <TableContainer
            component={Paper}
            sx={{ mb: 3, bgcolor: "rgba(0,0,0,0.2)" }}
          >
            <Table size="small">
              <TableBody>
                {Object.entries(sessionData.parameters || {}).map(
                  ([key, value]) => (
                    <TableRow key={key}>
                      <TableCell
                        component="th"
                        scope="row"
                        sx={{ color: "text.secondary" }}
                      >
                        {key.replace(/_/g, " ")}
                      </TableCell>
                      <TableCell align="right">{value}</TableCell>
                    </TableRow>
                  ),
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("common:metadata")}:
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
                    {t("common:created")}
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
