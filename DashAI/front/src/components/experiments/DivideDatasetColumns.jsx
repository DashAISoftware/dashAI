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
import { getColorByColumnType } from "../../utils";
import { useTranslation } from "react-i18next";

function DivideDatasetColumns({
  allColumnNames,
  columnTypes = {},
  selectedInputColumnNames,
  onInputColumnNamesChange,
  selectedOutputColumnNames,
  onOutputColumnNamesChange,
  inputError = false,
  inputHelperText = "",
  outputError = false,
  outputHelperText = "",
  disabled = false,
}) {
  const { t } = useTranslation(["experiments", "common"]);

  const handleInputAutocompleteChange = (event, newValue) => {
    onInputColumnNamesChange(newValue);
  };

  const handleOutputAutocompleteChange = (event, newValue) => {
    onOutputColumnNamesChange(newValue);
  };

  const getColumnLabel = (columnName) => {
    const columnType = columnTypes[columnName];
    if (columnType && columnType.type) {
      return `${columnName} (${columnType.type})`;
    }
    return columnName;
  };

  const renderColumnOption = (props, option) => {
    const { key, ...otherProps } = props;
    const columnType = columnTypes[option];
    const typeColor = columnType?.type
      ? getColorByColumnType(columnType.type)
      : null;

    return (
      <Box
        component="li"
        key={key}
        {...otherProps}
        sx={{ display: "flex", alignItems: "center", gap: 1 }}
      >
        <span>{option}</span>
        {columnType && columnType.type && (
          <Chip
            label={columnType.type}
            size="small"
            sx={{
              backgroundColor: typeColor,
              color: "#fff",
              fontWeight: 600,
              fontSize: "0.7rem",
              height: "20px",
            }}
          />
        )}
      </Box>
    );
  };

  const renderTags = (value, getTagProps) => {
    return value.map((option, index) => {
      const { key, ...tagProps } = getTagProps({ index });
      const columnType = columnTypes[option];
      const typeColor = columnType?.type
        ? getColorByColumnType(columnType.type)
        : null;

      const label =
        columnType && columnType.type ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <span>{option}</span>
            <Chip
              label={columnType.type}
              size="small"
              sx={{
                backgroundColor: typeColor,
                color: "#fff",
                fontWeight: 600,
                fontSize: "0.65rem",
                height: "16px",
              }}
            />
          </Box>
        ) : (
          option
        );

      return <Chip key={key} label={label} {...tagProps} />;
    });
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
          sx={{ mb: 2, color: "grey" }}
        >
          {t("experiments:label.selectInputOutputColumnsDescription")}
        </Typography>
      </Grid>

      <Autocomplete
        data-tour="dataset-input-columns-autocomplete"
        multiple
        id="dataset-input-columns-autocomplete"
        options={allColumnNames}
        value={selectedInputColumnNames}
        onChange={handleInputAutocompleteChange}
        getOptionLabel={(option) => option}
        renderOption={renderColumnOption}
        renderTags={renderTags}
        filterSelectedOptions
        disableCloseOnSelect
        fullWidth
        renderInput={(params) => (
          <TextField
            {...params}
            required
            label="Input Columns"
            error={inputError}
            helperText={inputHelperText}
            placeholder={
              allColumnNames.length > 0
                ? t("common:selectColumns")
                : t("common:loadingColumns")
            }
          />
        )}
        sx={{ mb: 2 }}
        disabled={disabled || allColumnNames.length === 0}
      />

      <Autocomplete
        data-tour="dataset-output-columns-autocomplete"
        multiple
        id="dataset-output-columns-autocomplete"
        options={allColumnNames}
        value={selectedOutputColumnNames}
        onChange={handleOutputAutocompleteChange}
        getOptionLabel={(option) => option}
        renderOption={renderColumnOption}
        renderTags={renderTags}
        filterSelectedOptions
        fullWidth
        renderInput={(params) => (
          <TextField
            {...params}
            required
            label="Output Columns"
            error={outputError}
            helperText={outputHelperText}
            placeholder={
              allColumnNames.length > 0
                ? t("common:selectColumns")
                : t("common:loadingColumns")
            }
          />
        )}
        sx={{ mb: 2 }}
        disabled={disabled || allColumnNames.length === 0}
      />
    </React.Fragment>
  );
}

DivideDatasetColumns.propTypes = {
  allColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnTypes: PropTypes.object,
  selectedInputColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  onInputColumnNamesChange: PropTypes.func.isRequired,
  selectedOutputColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  onOutputColumnNamesChange: PropTypes.func.isRequired,
  inputError: PropTypes.bool,
  inputHelperText: PropTypes.string,
  outputError: PropTypes.bool,
  outputHelperText: PropTypes.string,
  disabled: PropTypes.bool,
};

export default DivideDatasetColumns;
