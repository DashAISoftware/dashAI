import { Box, Typography } from "@mui/material";
import PropTypes from "prop-types";
import { useMemo } from "react";
import FormSchema from "../../shared/FormSchema";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import { generateSequentialName } from "../../../utils/nameGenerator";

/**
 * Right sidebar component for configuring dataloader parameters
 * Similar to ParamsBar in Generative section
 *
 * @param {string} selectedDataloader - The dataloader type to configure
 * @param {object} formSubmitRef - The reference to the form submit function
 * @param {function} setError - The function to set the error state
 * @param {array} existingDatasets - Array of existing datasets to avoid name conflicts
 * @param {function} onValuesChange - Callback function called when form values change
 */
export default function DataloaderConfigBar({
  selectedDataloader,
  formSubmitRef,
  setError,
  existingDatasets = [],
  onValuesChange,
}) {
  const { defaultName } = useMemo(
    () =>
      generateSequentialName({
        base: "Dataset",
        items: existingDatasets,
      }),
    [existingDatasets],
  );

  if (!selectedDataloader) {
    return (
      <Box
        display="flex"
        height="100%"
        width="100%"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        bgcolor="background.box"
        borderRadius={2}
        p={3}
      >
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", textAlign: "center" }}
        >
          Select a dataloader to configure parameters
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      display="flex"
      height="100%"
      width="100%"
      flexDirection="column"
      justifyContent="flex-start"
      overflow="auto"
      bgcolor="background.box"
      borderRadius={2}
    >
      {/* Header */}
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        px={2}
        pt={2}
        pb={1}
      >
        <Typography
          sx={{
            fontSize: "16px",
            whiteSpace: "normal",
            wordBreak: "break-word",
            fontWeight: 500,
            textAlign: "center",
          }}
        >
          Dataloader Configuration
        </Typography>
      </Box>

      {/* Configuration Form */}
      <Box sx={{ px: 2, pb: 2, flex: 1, overflow: "auto" }}>
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", mb: 2, textAlign: "center" }}
        >
          {selectedDataloader}
        </Typography>

        <FormSchemaContainer>
          <FormSchema
            autoSave
            model={selectedDataloader}
            formSubmitRef={formSubmitRef}
            setError={setError}
            initialValues={{ name: defaultName }}
            onValuesChange={onValuesChange}
            showBorder={false}
          />
        </FormSchemaContainer>
      </Box>
    </Box>
  );
}

DataloaderConfigBar.propTypes = {
  selectedDataloader: PropTypes.string,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }),
  setError: PropTypes.func,
  existingDatasets: PropTypes.array,
  onValuesChange: PropTypes.func,
};
