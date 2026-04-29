import React from "react";
import PropTypes from "prop-types";
import { Box, Stack, Typography, Chip, Divider } from "@mui/material";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";

function getLabel(component) {
  return component.display_name || component.name;
}

function getDescription(component) {
  return component.description ?? component.schema?.description ?? "";
}

function ComponentDetailsPanel({ component, getIcon, extraSections }) {
  const { t } = useTranslation("custom");

  return (
    <SideBar>
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          height: "100%",
          width: "100%",
        }}
      >
        {/* Title */}
        <Box
          sx={{
            p: 2,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            height: 70,
          }}
        >
          <Typography variant="h6" color="text.primary">
            {t("componentDetails")}
          </Typography>
        </Box>

        <Divider sx={{ width: "100%", bgcolor: "divider" }} />

        {/* Content */}
        {!component || !component.name ? (
          <Box
            sx={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 3,
            }}
          >
            <Typography variant="body2" color="text.secondary" textAlign="center">
              {t("selectAnItemToShowInfo")}
            </Typography>
          </Box>
        ) : (
          <Box sx={{ flex: 1, overflowY: "auto" }}>
            <Stack spacing={3} sx={{ p: 3 }}>
              <Stack direction="row" spacing={1.5} alignItems="flex-start">
                {getIcon?.(component) && (
                  <Box
                    sx={{
                      p: 1.25,
                      borderRadius: 1,
                      bgcolor: "primary.main",
                      color: "primary.contrastText",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {getIcon(component)}
                  </Box>
                )}
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="subtitle1" fontWeight={600} noWrap>
                    {getLabel(component)}
                  </Typography>
                  {component.type && (
                    <Typography variant="caption" color="text.secondary">
                      {component.type}
                    </Typography>
                  )}
                </Box>
              </Stack>

              <Box>
                <Typography
                  variant="overline"
                  color="text.secondary"
                  sx={{ letterSpacing: 1 }}
                >
                  {t("description")}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5, lineHeight: 1.6 }}>
                  {getDescription(component) || t("noDescriptionAvailable")}
                </Typography>
              </Box>

              {(component.schema?.tags || component.metadata?.tags || []).length > 0 && (
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ letterSpacing: 1 }}
                  >
                    {t("tags")}
                  </Typography>
                  <Stack
                    direction="row"
                    spacing={0.5}
                    flexWrap="wrap"
                    useFlexGap
                    sx={{ mt: 0.5 }}
                  >
                    {(component.schema?.tags || component.metadata?.tags).map((tag) => (
                      <Chip key={tag} label={tag} size="small" variant="outlined" />
                    ))}
                  </Stack>
                </Box>
              )}

              {extraSections &&
                extraSections.map((section) => (
                  <Box key={section.title}>
                    <Divider sx={{ mb: 2 }} />
                    <Typography
                      variant="overline"
                      color="text.secondary"
                      sx={{ letterSpacing: 1 }}
                    >
                      {section.title}
                    </Typography>
                    <Box sx={{ mt: 0.5 }}>{section.content}</Box>
                  </Box>
                ))}
            </Stack>
          </Box>
        )}
      </Box>
    </SideBar>
  );
}

ComponentDetailsPanel.propTypes = {
  component: PropTypes.shape({
    name: PropTypes.string,
    display_name: PropTypes.string,
    type: PropTypes.string,
    description: PropTypes.string,
    schema: PropTypes.object,
    metadata: PropTypes.object,
  }),
  getIcon: PropTypes.func,
  extraSections: PropTypes.arrayOf(
    PropTypes.shape({
      title: PropTypes.string.isRequired,
      content: PropTypes.node.isRequired,
    }),
  ),
};

export default ComponentDetailsPanel;
