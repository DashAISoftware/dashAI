import { Box, TextField, Typography } from "@mui/material";
import PropTypes from "prop-types";
import { useCallback, useRef, useState } from "react";
import { useTheme } from "@mui/material/styles";
import FormSchema from "../../shared/FormSchema";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import FormInputWrapper from "../../configurableObject/Inputs/FormInputWrapper";
import InputWithDebounce from "../../shared/InputWithDebounce";
import { generateSequentialName } from "../../../utils/nameGenerator";
import FormSchemaFieldCard from "../../shared/FormSchemaFieldCard";
import { useTranslation } from "react-i18next";
import SideBar from "../../threeSectionLayout/panelContainers/SideBar";

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
  onValuesChange,
}) {
  const [inferenceRows, setInferenceRows] = useState(1000);
  const schemaValuesRef = useRef({});
  const { t } = useTranslation(["common", "datasets"]);
  const theme = useTheme();

  // Handler for when FormSchema values change - merge with inference_rows
  const handleFormSchemaValuesChange = useCallback(() => {
    const values = formSubmitRef?.current?.values || {};
    schemaValuesRef.current = values;
    if (onValuesChange) {
      onValuesChange({ ...values, inference_rows: inferenceRows });
    }
  }, [formSubmitRef, inferenceRows, onValuesChange]);

  // Handler for when inference_rows changes - merge with schema values
  const handleInferenceRowsChange = useCallback(
    (val) => {
      const numeric = val ? Math.max(2, Number(val)) : 2;
      setInferenceRows(numeric);
      if (onValuesChange) {
        onValuesChange({ ...schemaValuesRef.current, inference_rows: numeric });
      }
    },
    [onValuesChange],
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
        borderBottom={`0.1px solid ${(theme) => theme.palette.divider}`}
        p={3}
      >
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", textAlign: "center" }}
        >
          {t("datasets:label.selectDataloaderToConfigure")}
        </Typography>
      </Box>
    );
  }

  return (
    <SideBar data-tour="dataloader-config">
      <Box
        sx={{
          p: 2,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
          flexShrink: 0,
          height: 64,
          display: "flex",
          alignItems: "center",
        }}
      >
        <Typography variant="h6" color="text.primary">
          {t("datasets:label.dataloaderConfiguration")}
        </Typography>
      </Box>

      <Box sx={{ flex: 1, overflowY: "auto", px: 2, pt: 1, pb: 2 }}>
        <Box
          sx={{
            pb: 1,
          }}
        >
          <FormSchemaFieldCard
            label={t("datasets:label.inferenceRows")}
            description={t("datasets:label.inferenceRowsDescription")}
          >
            <Box sx={{ pt: 0.75 }}>
              <InputWithDebounce
                name="inference_rows"
                value={inferenceRows}
                onChange={handleInferenceRowsChange}
                type="number"
                variant="outlined"
                size="small"
                fullWidth
                slotProps={{ input: { min: 2 } }}
              />
            </Box>
          </FormSchemaFieldCard>
        </Box>
        <FormSchemaContainer>
          <FormSchema
            autoSave
            model={selectedDataloader}
            formSubmitRef={formSubmitRef}
            setError={setError}
            initialValues={{}}
            onValuesChange={handleFormSchemaValuesChange}
            showBorder={false}
          />
        </FormSchemaContainer>
      </Box>
    </SideBar>
  );
}

DataloaderConfigBar.propTypes = {
  selectedDataloader: PropTypes.string,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }),
  setError: PropTypes.func,
  onValuesChange: PropTypes.func,
};
