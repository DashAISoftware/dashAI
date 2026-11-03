import React from "react";
import PropTypes from "prop-types";
import { Box, Stack, Typography, Divider } from "@mui/material";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import DescriptionText from "../shared/DescriptionText";
import TagBadges from "../shared/TagBadges";
import { useTheme } from "@mui/material/styles";

function getLabel(component) {
  return component.display_name || component.name;
}

function getDescription(component) {
  return component.description ?? component.schema?.description ?? "";
}

function ComponentDetailsPanel({
  component,
  getIcon,
  extraSections,
  categoryKey = "type",
  dataTour,
}) {
  const { t } = useTranslation("custom");
  const theme = useTheme();

  return (
    <SideBar data-tour={dataTour}>
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
            p: 4,
            borderBottom: `1px solid ${theme.palette.ui.border}`,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            height: 64,
          }}
        >
          <Typography variant="h6" color="text.primary">
            {t("componentDetails")}
          </Typography>
        </Box>

        {/* Content */}
        {!component || !component.name ? (
          <Box
            sx={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              p: 6,
            }}
          >
            <Typography
              variant="body2"
              color="text.secondary"
              textAlign="center"
            >
              {t("selectAnItemToShowInfo")}
            </Typography>
          </Box>
        ) : (
          <Box sx={{ flex: 1, overflowY: "auto" }}>
            <Stack spacing={4} sx={{ p: 4 }}>
              <Stack direction="row" spacing={3} alignItems="flex-start">
                {getIcon?.(component) && (
                  <Box
                    sx={{
                      p: 3,
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
                    {component.display_name || component.name}
                  </Typography>
                  {component[categoryKey] && (
                    <Typography variant="caption" color="text.secondary">
                      {component[categoryKey]}
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
                <Typography variant="body2" sx={{ mt: 1, lineHeight: 1.6 }}>
                  {getDescription(component) ? (
                    <DescriptionText text={getDescription(component)} />
                  ) : (
                    t("noDescriptionAvailable")
                  )}
                </Typography>
              </Box>

              {(component.schema?.tags || component.metadata?.tags || [])
                .length > 0 && (
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ letterSpacing: 1 }}
                  >
                    {t("tags")}
                  </Typography>
                  <TagBadges
                    tags={component.schema?.tags || component.metadata?.tags}
                    sx={{ mt: 1 }}
                  />
                </Box>
              )}

              {extraSections &&
                extraSections.map((section) => (
                  <Box key={section.title}>
                    <Divider sx={{ mb: 4 }} />
                    <Typography
                      variant="overline"
                      color="text.secondary"
                      sx={{ letterSpacing: 1 }}
                    >
                      {section.title}
                    </Typography>
                    <Box sx={{ mt: 1 }}>{section.content}</Box>
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
  categoryKey: PropTypes.string,
  dataTour: PropTypes.string,
  extraSections: PropTypes.arrayOf(
    PropTypes.shape({
      title: PropTypes.string.isRequired,
      content: PropTypes.node.isRequired,
    }),
  ),
};

export default ComponentDetailsPanel;
