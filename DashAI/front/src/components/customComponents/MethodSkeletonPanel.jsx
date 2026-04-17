import React from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTranslation } from "react-i18next";

function MethodSkeletonPanel({ baseInfo }) {
  const { t } = useTranslation("customComponents");

  if (!baseInfo) {
    return (
      <Box p={2}>
        <Typography variant="body2" color="text.secondary">
          {t("skeletonPanel.empty")}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 1, overflowY: "auto", height: "100%" }}>
      <Typography variant="subtitle2" gutterBottom>
        {t("skeletonPanel.abstractTitle")}
      </Typography>
      <Typography
        variant="caption"
        color="text.secondary"
        display="block"
        mb={1}
      >
        {t("skeletonPanel.abstractHelp")}
      </Typography>

      <Stack spacing={1}>
        {baseInfo.abstract_methods.map((m) => (
          <Accordion key={m.name} disableGutters>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box display="flex" alignItems="center" gap={1} width="100%">
                <Chip size="small" color="primary" label="abstract" />
                <Typography
                  variant="body2"
                  sx={{ fontFamily: "monospace", flexGrow: 1 }}
                >
                  {m.name}
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Typography
                variant="caption"
                sx={{
                  fontFamily: "monospace",
                  display: "block",
                  mb: 1,
                  whiteSpace: "pre-wrap",
                }}
              >
                def {m.name}
                {m.signature}
              </Typography>
              <Divider sx={{ my: 1 }} />
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ whiteSpace: "pre-wrap" }}
              >
                {m.docstring || t("skeletonPanel.noDocstring")}
              </Typography>
            </AccordionDetails>
          </Accordion>
        ))}
      </Stack>

      {baseInfo.class_attributes?.length > 0 && (
        <>
          <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
            {t("skeletonPanel.attrsTitle")}
          </Typography>
          <Stack spacing={0.5}>
            {baseInfo.class_attributes.map((a) => (
              <Box key={a.name} display="flex" alignItems="baseline" gap={1}>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {a.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  : {a.type}
                </Typography>
              </Box>
            ))}
          </Stack>
        </>
      )}
    </Box>
  );
}

export default MethodSkeletonPanel;
