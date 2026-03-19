import React from "react";
import CustomLayout from "../../../components/custom/CustomLayout";
import {
  Button,
  Card,
  Paper,
  CardHeader,
  CardContent,
  Typography,
  Grid,
} from "@mui/material";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import { useParams, useNavigate } from "react-router-dom";
import PluginsDetailsTab from "./PluginsDetailsTab";
import PluginTags from "./PluginsTags";
import usePluginsDetails from "../hooks/usePluginsDetails";
import { PluginStatus } from "../../../types/plugin";
import usePluginsUpdate from "../hooks/usePluginsUpdate";
import usePluginsUpgrade from "../hooks/usePluginsUpgrade";
import Markdown from "react-markdown";
import CircularProgress from "@mui/material/CircularProgress";
import { Trans, useTranslation } from "react-i18next";
import PropTypes from "prop-types";

function PluginsActions({
  installLoading,
  plugin,
  updatePlugin,
  upgradePlugin,
}) {
  const { t } = useTranslation(["plugins"]);
  return (
    <Grid container columnGap={2}>
      {installLoading ? (
        <Button size="medium" variant="outlined" disabled>
          <CircularProgress size={24} />
        </Button>
      ) : (
        <Button onClick={() => updatePlugin()} size="medium" variant="outlined">
          {[PluginStatus.INSTALLED, PluginStatus.DOWNLOADED].includes(
            plugin.status,
          )
            ? t("plugins:button.uninstall")
            : t("plugins:button.install")}
        </Button>
      )}
      {[PluginStatus.INSTALLED, PluginStatus.DOWNLOADED].includes(
        plugin.status,
      ) && (
        <Button
          onClick={() => upgradePlugin()}
          size="medium"
          variant="outlined"
          disabled={plugin.installed_version === plugin.lastest_version}
        >
          {t("plugins:button.upgrade")}
        </Button>
      )}
    </Grid>
  );
}
PluginsActions.propTypes = {
  installLoading: PropTypes.bool.isRequired,
  plugin: PropTypes.object.isRequired,
  updatePlugin: PropTypes.func.isRequired,
  upgradePlugin: PropTypes.func.isRequired,
};

/**
 * component for plugin details
 * @returns
 */
function PluginsDetails() {
  const navigate = useNavigate();
  const { category, id } = useParams();
  const [updatePluginFlag, setUpdatePluginFlag] = React.useState(true);
  const { plugin, loading, error } = usePluginsDetails({
    pluginId: id,
    updatePluginFlag,
    setUpdatePluginFlag,
  });
  const { t } = useTranslation(["plugins"]);

  const handleReturnClick = () => {
    navigate(`/app/plugins/${category}`);
  };

  const { updatePlugin, loading: installLoading } = usePluginsUpdate({
    pluginId: plugin.id,
    newStatus: [PluginStatus.INSTALLED, PluginStatus.DOWNLOADED].includes(
      plugin.status,
    )
      ? PluginStatus.REGISTERED
      : PluginStatus.INSTALLED,
    onSuccess: () => {
      setUpdatePluginFlag(true);
    },
  });

  const { upgradePlugin } = usePluginsUpgrade({
    pluginId: plugin.id,
  });

  const tabs = [
    {
      label: t("plugins:label.details"),
      component: <Markdown>{plugin.description}</Markdown>,
    },
  ];

  return (
    <CustomLayout>
      <Button
        startIcon={<ArrowBackIosNewIcon />}
        onClick={() => {
          handleReturnClick();
        }}
      >
        {t("plugins:button.return")}
      </Button>
      {loading && (
        <Paper sx={{ p: 2, mt: 2, minHeight: "75vh" }}>
          <Grid size={{ xs: 12 }} height={"218px"}>
            <Card
              sx={{
                height: "100%",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
              }}
            >
              <CircularProgress />
            </Card>
          </Grid>
        </Paper>
      )}
      {!loading && !error && (
        <Paper sx={{ p: 2, mt: 2, minHeight: "75vh" }}>
          <Card
            sx={{
              width: "100%",

              boxShadow: "0",
              alignItems: "center",
            }}
          >
            <CardHeader
              title={plugin.name.replace("dashai-", "")}
              sx={{
                pb: 0,
                width: "100%",
              }}
              subheader={
                <Grid container direction={"column"} rowGap={1}>
                  <Grid>
                    {[PluginStatus.INSTALLED, PluginStatus.DOWNLOADED].includes(
                      plugin.status,
                    ) ? (
                      <Typography>
                        <Trans i18nKey="plugins:label.versionInstalledLatestAvailable">
                          Version installed: {plugin.installed_version} | Latest
                          version available: {plugin.lastest_version}
                        </Trans>
                      </Typography>
                    ) : (
                      <Typography>
                        {t("plugins:label.version", {
                          version: plugin.installed_version,
                        })}
                      </Typography>
                    )}
                  </Grid>
                  <Grid>
                    <PluginTags tags={plugin.tags} />
                  </Grid>
                  <Grid> {plugin.summary} </Grid>
                </Grid>
              }
              slotProps={{
                title: {
                  variant: "h4",
                  noWrap: true,
                },
              }}
            />
            <CardContent sx={{ pb: 0 }}>
              <PluginsActions
                installLoading={installLoading}
                plugin={plugin}
                updatePlugin={updatePlugin}
                upgradePlugin={upgradePlugin}
              />
            </CardContent>
          </Card>
          <PluginsDetailsTab tabs={tabs}></PluginsDetailsTab>
        </Paper>
      )}
    </CustomLayout>
  );
}

export default PluginsDetails;
