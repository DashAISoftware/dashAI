import React from "react";
import PropTypes from "prop-types";
import {
  Grid,
  Typography,
  Autocomplete,
  TextField,
  Box,
  Chip,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { getColorByColumnType } from "../../../utils";
import { useTranslation } from "react-i18next";

/**
 * One column selector per role the task declares.
 *
 * The roles come from the task's metadata (`column_roles`), so this never
 * names a role: a classifier shows its features and its target, a forecaster
 * its index, series and exogenous columns, a clustering task only its
 * features. A role that takes no columns (max 0) gets no selector.
 *
 * Options are plain strings: an original column name, or the synthetic key
 * of a ref to a converter's output (see sessionColumnRefs), shown through
 * `optionLabels`.
 *
 * The first role the preprocessing may transform and the first protected
 * one carry the tour anchors the input and output selectors used to.
 */
function RoleColumnSelectors({
  roles,
  selection,
  onChange,
  optionsFor,
  labelFor = (role) => role.label,
  columnTypes = {},
  optionLabels = {},
  errorFor = () => false,
  helperTextFor = () => "",
  disabledFor = () => false,
  disabled = false,
}) {
  const { t } = useTranslation(["experiments", "common"]);
  const theme = useTheme();

  const getOptionLabel = (option) => optionLabels[option] || option;

  const typeChip = (option, small) => {
    const columnType = columnTypes[option];
    if (!columnType?.type) return null;
    return (
      <Chip
        label={columnType.type}
        size="small"
        sx={{
          backgroundColor: getColorByColumnType(columnType.type, theme),
          color: "#fff",
          fontWeight: 600,
          fontSize: small ? "0.65rem" : "0.7rem",
          height: small ? "16px" : "20px",
        }}
      />
    );
  };

  const renderColumnOption = (props, option) => {
    const { key, ...otherProps } = props;
    return (
      <Box
        component="li"
        key={key}
        {...otherProps}
        sx={{ display: "flex", alignItems: "center", gap: 2 }}
      >
        <span>{getOptionLabel(option)}</span>
        {typeChip(option, false)}
      </Box>
    );
  };

  const renderTags = (value, getTagProps) =>
    value.map((option, index) => {
      const { key, ...tagProps } = getTagProps({ index });
      const chip = typeChip(option, true);
      const label = chip ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <span>{getOptionLabel(option)}</span>
          {chip}
        </Box>
      ) : (
        getOptionLabel(option)
      );
      return <Chip key={key} label={label} {...tagProps} />;
    });

  const shown = roles.filter((role) => role.max !== 0);
  const firstTransformable = shown.find((role) => role.transformable)?.name;
  const firstProtected = shown.find((role) => !role.transformable)?.name;
  const tourAnchor = (role) => {
    if (role.name === firstTransformable) {
      return "dataset-input-columns-autocomplete";
    }
    if (role.name === firstProtected) {
      return "dataset-output-columns-autocomplete";
    }
    return undefined;
  };

  return (
    <React.Fragment>
      <Grid size={{ xs: 12 }}>
        <Typography variant="subtitle1" component="h3" sx={{ mb: 0 }}>
          {t("experiments:label.selectDatasetColumns")}
        </Typography>
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Typography
          variant="caption"
          component="h3"
          sx={{ mb: 8, color: "grey" }}
        >
          {t("experiments:label.selectInputOutputColumnsDescription")}
        </Typography>
      </Grid>

      {shown.map((role) => {
        const options = optionsFor(role);
        return (
          <Autocomplete
            key={role.name}
            data-tour={tourAnchor(role)}
            multiple
            id={`dataset-role-${role.name}-autocomplete`}
            options={options}
            value={selection[role.name] || []}
            onChange={(event, newValue) => onChange(role.name, newValue)}
            getOptionLabel={getOptionLabel}
            renderOption={renderColumnOption}
            renderTags={renderTags}
            filterSelectedOptions
            disableCloseOnSelect={role.max !== 1}
            fullWidth
            renderInput={(params) => (
              <TextField
                {...params}
                required={role.required}
                label={labelFor(role)}
                error={errorFor(role)}
                helperText={helperTextFor(role)}
                placeholder={
                  options.length > 0
                    ? t("common:selectColumns")
                    : t("common:loadingColumns")
                }
              />
            )}
            sx={{ mb: 8 }}
            disabled={disabled || disabledFor(role) || options.length === 0}
          />
        );
      })}
    </React.Fragment>
  );
}

RoleColumnSelectors.propTypes = {
  // The task's declared roles, as its metadata lists them.
  roles: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      label: PropTypes.string,
      min: PropTypes.number,
      max: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
      required: PropTypes.bool,
      transformable: PropTypes.bool,
    }),
  ).isRequired,
  // Role name to the selected option keys.
  selection: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
  // The option keys a role can pick from.
  optionsFor: PropTypes.func.isRequired,
  labelFor: PropTypes.func,
  columnTypes: PropTypes.object,
  optionLabels: PropTypes.object,
  errorFor: PropTypes.func,
  helperTextFor: PropTypes.func,
  disabledFor: PropTypes.func,
  disabled: PropTypes.bool,
};

export default RoleColumnSelectors;
