import React from "react";
import { Box, Typography, Autocomplete, TextField, Chip } from "@mui/material";

export default function DatasetAutocomplete({
  datasets,
  selectedDataset,
  setSelectedDataset,
}) {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Box width="100%">
      <Box sx={{ width: "100%", mx: "auto" }}>
        <Autocomplete
          options={datasets}
          getOptionLabel={(option) => option.name}
          value={selectedDataset}
          onChange={(event, newValue) => {
            setSelectedDataset(newValue);
          }}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Select a dataset"
              variant="outlined"
              placeholder="Type to search datasets..."
            />
          )}
          renderOption={(props, option) => (
            <Box component="li" {...props}>
              <Box
                sx={{ display: "flex", flexDirection: "column", width: "100%" }}
              >
                <Typography variant="body1" fontWeight="medium">
                  {option.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Created: {formatDate(option.created)}
                </Typography>
              </Box>
            </Box>
          )}
          sx={{ mb: 3 }}
        />

        {selectedDataset && (
          <Box
            sx={{
              mt: 3,
              p: 3,
              border: 1,
              borderColor: "divider",
              borderRadius: 2,
            }}
          >
            <Typography variant="h6" gutterBottom>
              Selected Dataset
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="body2" fontWeight="medium">
                  Name:
                </Typography>
                <Chip label={selectedDataset.name} size="small" />
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography variant="body2" fontWeight="medium">
                  Created:
                </Typography>
                <Typography variant="body2">
                  {formatDate(selectedDataset.created)}
                </Typography>
              </Box>
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  );
}
