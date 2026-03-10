import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Card,
  CardContent,
  Box,
  styled,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTranslation } from "react-i18next";

// Styled component for the scrollable area
const ScrollableContent = styled(DialogContent)(({ theme }) => ({
  maxHeight: "calc(80vh - 120px)",
  overflowY: "auto",
  "&::-webkit-scrollbar": {
    width: "8px",
  },
  "&::-webkit-scrollbar-track": {
    background: theme.palette.background.paper,
  },
  "&::-webkit-scrollbar-thumb": {
    backgroundColor: theme.palette.divider,
    borderRadius: "4px",
  },
}));

export default function SessionHistoryModal({
  historyChanges,
  taskName,
  open,
  setOpen,
}) {
  const [expanded, setExpanded] = useState(false);
  const { t } = useTranslation(["generative", "common"]);

  const handleOpen = () => setOpen(true);
  const handleClose = () => setOpen(false);

  const handleChange = (panel) => (event, isExpanded) => {
    setExpanded(isExpanded ? panel : false);
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={handleClose}
        fullWidth
        slotProps={{
          paper: {
            sx: {
              bgcolor: "background.paper",
              color: "text.primary",
              maxHeight: "80vh",
              maxWidth: 600,
            },
          },
        }}
      >
        <DialogTitle>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
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
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Typography variant="body2" color="text.secondary" mt={1}>
            {t("generative:label.parameterChangeHistory")}
          </Typography>
        </DialogTitle>

        <ScrollableContent dividers>
          {historyChanges?.map((event) => (
            <Accordion
              key={event.id}
              expanded={expanded === event.id}
              onChange={handleChange(event.id)}
              sx={{
                mb: 1,
                bgcolor: "background.paper",
                "&:before": {
                  display: "none",
                },
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
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontFamily: "monospace" }}
                  >
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
        </ScrollableContent>
      </Dialog>
    </>
  );
}
