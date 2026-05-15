import { useState } from "react";
import {
  Modal,
  IconButton,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Card,
  CardContent,
  Box,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTranslation } from "react-i18next";

export default function SessionHistoryModal({
  historyChanges,
  taskName,
  open,
  setOpen,
}) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslation(["generative", "common"]);

  const handleClose = () => setOpen(false);

  const handleChange = (panel) => (event, isExpanded) => {
    setExpanded(isExpanded ? panel : false);
  };

  return (
    <Modal open={open} onClose={handleClose}>
      <Box
        sx={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: { xs: "90%", sm: 600 },
          maxHeight: "80vh",
          bgcolor: "background.paper",
          borderRadius: 2,
          boxShadow: 12,
          p: 0,
          outline: "none",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6">Change History</Typography>
            <Chip
              label={taskName}
              variant="outlined"
              size="small"
              sx={{ ml: 1 }}
            />
          </Box>
          <IconButton
            onClick={handleClose}
            size="small"
            sx={{ color: "text.secondary" }}
          >
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Content */}
        <Box
          sx={{
            p: 3,
            display: "flex",
            flexDirection: "column",
            gap: 2,
            overflowY: "auto",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            {t("generative:label.parameterChangeHistory")}
          </Typography>

          {historyChanges?.map((event) => (
            <Accordion
              key={event.id}
              expanded={expanded === event.id}
              onChange={handleChange(event.id)}
              sx={{
                bgcolor: "background.paper",
                "&:before": { display: "none" },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{
                  "&:hover": {
                    bgcolor: "action.hover",
                    borderRadius: 1,
                  },
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: { xs: "column", sm: "row" },
                    alignItems: { xs: "flex-start", sm: "center" },
                    gap: { xs: 0.5, sm: 2 },
                    width: "100%",
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    {new Date(event.timestamp).toLocaleString()}
                  </Typography>
                  <Typography variant="body1" sx={{ flexGrow: 1 }}>
                    {event.description}
                  </Typography>
                  <Chip
                    label={`${event.changes.length} changes`}
                    size="small"
                    color="primary"
                    sx={{ height: 24 }}
                  />
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ pt: 1, pb: 2 }}>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {event.changes.map((change, index) => (
                    <Card
                      key={`${event.id}-change-${index}`}
                      variant="outlined"
                      sx={{
                        bgcolor: "background.default",
                        borderColor: "divider",
                      }}
                    >
                      <CardContent
                        sx={{
                          p: 2,
                          "&:last-child": { pb: 2 },
                          overflowX: "auto",
                        }}
                      >
                        <Box
                          sx={{
                            display: "grid",
                            gridTemplateColumns: {
                              xs: "1fr",
                              sm: "1fr auto auto",
                            },
                            gap: 2,
                            alignItems: "center",
                          }}
                        >
                          <Typography variant="body1" fontWeight="medium">
                            {change.parameter}
                          </Typography>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">
                              {t("common:from")}:
                            </Typography>
                            <Chip
                              label={change.oldValue.toString()}
                              variant="outlined"
                              size="small"
                            />
                          </Box>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            <Typography variant="body2" color="text.secondary">
                              {t("common:to")}:
                            </Typography>
                            <Chip
                              label={change.newValue.toString()}
                              color="primary"
                              size="small"
                            />
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>
      </Box>
    </Modal>
  );
}
