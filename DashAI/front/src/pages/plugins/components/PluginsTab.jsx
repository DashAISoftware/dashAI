import React from "react";
import { Box, Button, Grid, Tab, Tabs, Typography } from "@mui/material";
import { TabContext, TabPanel } from "@mui/lab";
import PropTypes from "prop-types";
import PluginsContent from "./PluginsContent";
import { Link } from "react-router-dom";
import usePluginsTab from "../hooks/usePluginsTab";
import { Update as UpdateIcon } from "@mui/icons-material";
import { updatePluginsDBFromPypi as updatePluginsFromPypi } from "../../../api/plugins";
import { useTranslation } from "react-i18next";

/**
 * component to display plugins main tabs
 * @param {boolean} refreshPluginsFlag
 * @param {function} setRefreshPluginsFlag
 * @returns
 */
function PluginsTab({ refreshPluginsFlag, setRefreshPluginsFlag }) {
  const { tabs, pluginTags, loading, tabValue, handleTabChange } =
    usePluginsTab({
      refreshPluginsFlag,
      setRefreshPluginsFlag,
    });
  const { t } = useTranslation(["plugins"]);

  return (
    <Box sx={{ width: "100%" }}>
      <TabContext value={tabValue}>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="tabs">
            {tabs.map(({ label, to }, i) => (
              <Tab
                component={Link}
                key={label}
                label={label}
                value={i.toString()}
                to={to}
              />
            ))}
          </Tabs>
        </Box>
        {tabs.map(({ label, plugins }, i) => (
          <TabPanel key={label} value={i.toString()} sx={{ p: 0 }}>
            <Grid
              container
              alignItems={"center"}
              justifyContent={"space-between"}
            >
              <Grid>
                <Typography variant="h4" py={2}>
                  {t("plugins:label.plugins", { label })}
                </Typography>
              </Grid>
              <Grid>
                <Button
                  variant="contained"
                  onClick={async () => {
                    setRefreshPluginsFlag(true);
                    try {
                      await updatePluginsFromPypi();
                    } catch (error) {
                      enqueueSnackbar(t("plugins:error.updatePlugins"), {
                        variant: "error",
                      });
                    }
                  }}
                  endIcon={<UpdateIcon />}
                >
                  {t("plugins:button.refresh")}
                </Button>
              </Grid>
            </Grid>
            <PluginsContent
              refreshPluginsFlag={refreshPluginsFlag}
              setRefreshPluginsFlag={setRefreshPluginsFlag}
              plugins={plugins}
              pluginTags={pluginTags}
              loading={loading}
            />
          </TabPanel>
        ))}
      </TabContext>
    </Box>
  );
}

PluginsTab.propTypes = {
  refreshPluginsFlag: PropTypes.bool.isRequired,
  setRefreshPluginsFlag: PropTypes.func.isRequired,
};

export default PluginsTab;
