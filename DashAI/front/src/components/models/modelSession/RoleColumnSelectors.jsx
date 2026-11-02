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
import { getColumnTypeLabel } from "../../../utils/typesLists";
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
 *
 * A role's maximum is held by the selector, never by trimming a pick: a role
 * that takes one column is a single selector, where picking another replaces
 * it in sight; one that takes a few disables the other options once it has
 * them.
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
        label={getColumnTypeLabel(columnType.type, t)}
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

  const valueChip = (option, itemProps) => {
    const { key, ...chipProps } = itemProps;
    const chip = typeChip(option, true);
    const label = chip ? (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <span>{getOptionLabel(option)}</span>
        {chip}
      </Box>
    ) : (
      getOptionLabel(option)
    );
    return <Chip key={key} label={label} {...chipProps} />;
  };

  // A single selector would show its column as plain text in the input, so
  // it gets the same chip, with the type, as each column of a multiple one.
  const renderValue = (value, getItemProps) =>
    Array.isArray(value)
      ? value.map((option, index) => valueChip(option, getItemProps({ index })))
      : valueChip(value, getItemProps());

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
        const picked = selection[role.name] || [];
        const single = role.max === 1;
        const full = typeof role.max === "number" && picked.length >= role.max;
        return (
          <Autocomplete
            key={role.name}
            data-tour={tourAnchor(role)}
            multiple={!single}
            id={`dataset-role-${role.name}-autocomplete`}
            options={options}
            value={single ? (picked[0] ?? null) : picked}
            onChange={(event, newValue) => {
              if (!single) {
                onChange(role.name, newValue);
              } else {
                onChange(role.name, newValue == null ? [] : [newValue]);
              }
            }}
            getOptionLabel={getOptionLabel}
            getOptionDisabled={(option) =>
              !single && full && !picked.includes(option)
            }
            renderOption={renderColumnOption}
            renderValue={renderValue}
            filterSelectedOptions
            disableCloseOnSelect={!single}
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
