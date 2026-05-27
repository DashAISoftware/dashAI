import React from "react";
import PluginsToolbar from "./PluginsToolbar";
import PropTypes from "prop-types";
import { Grid, Typography, Card } from "@mui/material";
import PluginCard from "./PluginsCard";
import usePluginsContent from "../hooks/usePluginsContent";
import CircularProgress from "@mui/material/CircularProgress";
import { useTranslation } from "react-i18next";

/**
 * component to render tab content: toolbar and plugins grid
 * @param {object} plugins plugins to show
 * @param {string[]} pluginTags
 * @param {boolean} refreshPluginsFlag
 * @param {function} setRefreshPluginsFlag
 * @param {boolean} loading
 * @returns
 */
function PluginsContent({
  plugins,
  pluginTags,
  refreshPluginsFlag,
  setRefreshPluginsFlag,
  loading,
}) {
  const {
    pluginsToShow,
    searchField,
    handleSearchFieldChange,
    type,
    handleTypeChange,
    sortBy,
    handleSortByChange,
  } = usePluginsContent({ plugins });

  const [cardView, setCardView] = React.useState(true);
  const handleCardViewChange = (event, newAlignment) => {
    if (newAlignment !== null) {
      setCardView(newAlignment);
    }
  };
  const { t } = useTranslation(["plugins"]);

  return (
    <>
      <PluginsToolbar
        cardView={cardView}
        handleCardViewChange={handleCardViewChange}
        searchField={searchField}
        handleSearchFieldChange={handleSearchFieldChange}
        type={type}
        handleTypeChange={handleTypeChange}
        sortBy={sortBy}
        handleSortByChange={handleSortByChange}
        pluginTags={pluginTags}
      />

      {/* Loading */}
      {loading && (
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
      )}

      {/* No plugins */}
      {!loading && !pluginsToShow.length && (
        <Grid size={{ xs: 12 }} height={"218px"}>
          <Card
            sx={{
              height: "100%",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <Typography variant="body1">
              {t("plugins:label.noPluginsToShow")}
            </Typography>
          </Card>
        </Grid>
      )}

      {/* Plugins Grid */}
      {!loading && !!pluginsToShow.length && (
        <Grid container spacing={2}>
          {pluginsToShow.map((plugin, i) => (
            <Grid
              key={i}
              size={{
                xl: cardView ? 4 : 12,
                lg: cardView ? 4 : 12,
                md: cardView ? 6 : 12,
                sm: 12,
                xs: 12,
              }}
              height={cardView ? "250px" : "auto"}
            >
              <PluginCard
                plugin={plugin}
                cardView={cardView}
                refreshPluginsFlag={refreshPluginsFlag}
                setRefreshPluginsFlag={setRefreshPluginsFlag}
              />
            </Grid>
          ))}
        </Grid>
      )}
    </>
  );
}

PluginsContent.propTypes = {
  plugins: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      author: PropTypes.string.isRequired,
      tags: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number.isRequired,
          name: PropTypes.string.isRequired,
          plugin_id: PropTypes.number.isRequired,
        }),
      ),
      status: PropTypes.oneOf([0, 1, 2, 3]).isRequired,
      summary: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      description_content_type: PropTypes.string.isRequired,
      created: PropTypes.string.isRequired,
      last_modified: PropTypes.string.isRequired,
    }),
  ).isRequired,
  refreshPluginsFlag: PropTypes.bool.isRequired,
  setRefreshPluginsFlag: PropTypes.func.isRequired,
  pluginTags: PropTypes.arrayOf(PropTypes.string).isRequired,
};

export default PluginsContent;
