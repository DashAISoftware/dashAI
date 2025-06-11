import React from "react";
import PropTypes from "prop-types";
import { Grid, Typography, Autocomplete, TextField } from "@mui/material";

function DivideDatasetColumns({
  allColumnNames,
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
  const handleInputAutocompleteChange = (event, newValue) => {
    onInputColumnNamesChange(newValue);
  };

  const handleOutputAutocompleteChange = (event, newValue) => {
    onOutputColumnNamesChange(newValue);
  };

  return (
    <React.Fragment>
      <Grid item xs={12}>
        <Typography variant="subtitle1" component="h3" sx={{ mb: 0 }}>
          Indicate which columns of the dataset will be used as input and
          output.
        </Typography>
      </Grid>
      <Grid item xs={12}>
        <Typography
          variant="caption"
          component="h3"
          sx={{ mb: 2, color: "grey" }}
        >
          Select column names from the lists.
        </Typography>
      </Grid>

      <Autocomplete
        multiple
        id="dataset-input-columns-autocomplete"
        options={allColumnNames}
        value={selectedInputColumnNames}
        onChange={handleInputAutocompleteChange}
        getOptionLabel={(option) => option} // Assuming allColumnNames are strings
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
                ? "Select columns"
                : "Loading columns..."
            }
          />
        )}
        sx={{ mb: 2 }}
        disabled={disabled || allColumnNames.length === 0}
      />

      <Autocomplete
        multiple
        id="dataset-output-columns-autocomplete"
        options={allColumnNames}
        value={selectedOutputColumnNames}
        onChange={handleOutputAutocompleteChange}
        getOptionLabel={(option) => option}
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
                ? "Select columns"
                : "Loading columns..."
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
