import React from "react";
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  IconButton,
  Typography,
} from "@mui/material";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { ChevronRight } from "@mui/icons-material";
import { useTheme } from "@mui/material/styles";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";

function PipelineTemplatesSidebar({ onToggle, templates = [], onSelectTemplate }) {
  const theme = useTheme();

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          minHeight: 64,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <AutoAwesomeIcon fontSize="small" sx={{ color: theme.palette.text.primary }} />
          <Typography variant="subtitle1">Prefabricated Pipelines</Typography>
        </Box>
        {onToggle && (
          <IconButton
            size="small"
            onClick={onToggle}
            sx={{ color: "text.secondary" }}
          >
            <ChevronRight />
          </IconButton>
        )}
      </Box>

      <Box sx={{ p: 1.5, overflowY: "auto", display: "grid", gap: 1.5, flex: 1 }}>
        {templates.map((template) => (
          <Card
            key={template.id}
            variant="outlined"
            sx={{ cursor: "pointer" }}
            onClick={() => onSelectTemplate?.(template.id)}
          >
            <CardContent sx={{ pb: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                {template.name}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 1.5 }}
              >
                {(template.labels || template.steps).join(" + ")}
              </Typography>
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {(template.labels || template.steps).map((step) => (
                  <Chip size="small" label={step} key={step} />
                ))}
              </Box>
            </CardContent>
            <CardActions sx={{ px: 2, pb: 1.5, pt: 0 }}>
              <Button
                size="small"
                onClick={(event) => {
                  event.stopPropagation();
                  onSelectTemplate?.(template.id);
                }}
              >
                Use template
              </Button>
            </CardActions>
          </Card>
        ))}
      </Box>
    </SideBar>
  );
}

export default PipelineTemplatesSidebar;
