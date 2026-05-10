import React from "react";
import {
  Grid,
  ToggleButtonGroup,
  ToggleButton,
  Select,
  FormControl,
  InputLabel,
  TextField,
  MenuItem,
  InputAdornment,
} from "@mui/material";
import ViewListIcon from "@mui/icons-material/ViewList";
import ViewModuleIcon from "@mui/icons-material/ViewModule";
import SearchIcon from "@mui/icons-material/Search";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

function PluginsToolbar({
  cardView,
  handleCardViewChange,
  searchField,
  handleSearchFieldChange,
  type,
  handleTypeChange,
  sortBy,
  handleSortByChange,
  pluginTags,
}) {
  const { t } = useTranslation(["plugins", "common"]);

  const sortByValues = [
    { value: "latest", label: t("plugins:label.latest") },
    { value: "oldest", label: t("plugins:label.oldest") },
  ];

  return (
    <Grid container justifyContent={"space-between"} paddingBottom={4}>
      <Grid container size={{ xs: 8 }} spacing={4}>
        <Grid size={{ xs: 8 }}>
          <TextField
            id="input-with-icon-textfield"
            label={t("common:search")}
            variant="outlined"
            value={searchField}
            onChange={handleSearchFieldChange}
            fullWidth
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              },
            }}
          />
        </Grid>
        <Grid>
          <FormControl variant="outlined" sx={{ minWidth: 120 }}>
            <InputLabel id="select-type-label">
              {t("plugins:label.tags")}
            </InputLabel>
            <Select
              id="select-type"
              value={type}
              onChange={handleTypeChange}
              label={t("common:type")}
              autoWidth
            >
              <MenuItem key={""} value={""}>
                {t("common:none")}
              </MenuItem>
              {pluginTags.map((pluginTag) => (
                <MenuItem key={pluginTag} value={pluginTag}>
                  {pluginTag}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
      </Grid>
      <Grid
        container
        size={{ xs: 4 }}
        spacing={4}
        display={"flex"}
        alignItems={"center"}
        justifyContent={"flex-end"}
      >
        <Grid>
          <ToggleButtonGroup
            value={cardView}
            exclusive
            onChange={handleCardViewChange}
            aria-label="card view mode"
          >
            <ToggleButton value={true} aria-label="grid view">
              <ViewModuleIcon />
            </ToggleButton>
            <ToggleButton value={false} aria-label="list view">
              <ViewListIcon />
            </ToggleButton>
          </ToggleButtonGroup>
        </Grid>

        <Grid>
          <FormControl variant="outlined" sx={{ minWidth: 120 }}>
            <InputLabel id="select-sort-by-label">
              {t("common:sortBy")}
            </InputLabel>
            <Select
              id="select-sort-by"
              value={sortBy}
              onChange={handleSortByChange}
              label={t("common:sortBy")}
            >
              {sortByValues.map((sortByValue) => (
                <MenuItem key={sortByValue.value} value={sortByValue.value}>
                  {sortByValue.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
      </Grid>
    </Grid>
  );
}

PluginsToolbar.propTypes = {
  cardView: PropTypes.bool.isRequired,
  handleCardViewChange: PropTypes.func.isRequired,
  searchField: PropTypes.string.isRequired,
  handleSearchFieldChange: PropTypes.func.isRequired,
  type: PropTypes.string.isRequired,
  handleTypeChange: PropTypes.func.isRequired,
  sortBy: PropTypes.string.isRequired,
  handleSortByChange: PropTypes.func.isRequired,
  pluginTags: PropTypes.array.isRequired,
};

export default PluginsToolbar;
