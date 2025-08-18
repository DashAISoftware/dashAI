import React, { useEffect, useState } from "react";
import { Box, Typography, Button, IconButton, Tooltip } from "@mui/material";

import { saveConverterList } from "../../../api/converter";
import { useExplorersAndConverters } from "../context/ExplorersAndConvertersContext";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import { useSnackbar } from "notistack";
import { ViewColumn } from "@mui/icons-material";
import HelpIcon from "@mui/icons-material/Help";
import ConverterClassColumnModal from "./ConverterClassColumnModal";

export default function FormSection({ converter, notebook, handleSubmit }) {
  const [formStep, setFormStep] = useState(0); // 0 = scope, 1 = parameters
  const [initialParams, setInitialParams] = useState({});
  const [open, setOpen] = useState(false);
  const [classColumnInitialValue, setClassColumnInitialValue] = useState(null);
  const [formValues, setFormValues] = useState({
    notebook_id: notebook.id,
    converter: converter.name,
    parameters: {
      params: {},
      scope: {
        columns: [],
        rows: [],
      },
      order: 1,
      target_index: null,
    },
  });

  const { explorersAndConverters, setExplorersAndConverters } =
    useExplorersAndConverters();
  const { enqueueSnackbar } = useSnackbar();

  const handleSaveConverter = async (params) => {
    enqueueSnackbar(`Converter ${converter.name} created successfully `, {
      variant: "success",
    });

    const copyValues = structuredClone(formValues);
    copyValues.parameters.params = params;

    console.log("Saving converter with params:", copyValues);
    handleSubmit();
  };

  useEffect(() => {
    const copyValues = structuredClone(formValues);
    copyValues.parameters.target_index = classColumnInitialValue;
    setFormValues(copyValues);
  }, [classColumnInitialValue]);

  return (
    <Box
      sx={{
        p: 2,
        borderTop: "1px solid",
        borderColor: "divider",
        height: "65%",
        overflow: "auto",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Typography
        variant="body2"
        color="text.secondary"
        gutterBottom
        textAlign="center"
      >
        Configure the settings for your dataset conversion
      </Typography>

      {/* Step content */}
      {formStep === 0 && (
        <Box flex={1}>
          <Typography variant="subtitle2" gutterBottom>
            Step 1: Select Scope
          </Typography>
          {/* placeholder: scope selection UI */}
          <Typography variant="body2" color="text.secondary">
            Here you will configure which columns and rows to apply the
            converter to.
          </Typography>
        </Box>
      )}

      {formStep === 1 && (
        <Box flex={1}>
          <Typography variant="subtitle2" gutterBottom>
            Step 2: Configure Parameters
          </Typography>
          <FormSchemaContainer>
            <FormSchemaWithSelectedModel
              onFormSubmit={handleSaveConverter}
              modelToConfigure={converter.name}
              initialValues={initialParams}
              onCancel={() => setFormStep(0)}
            />
          </FormSchemaContainer>
        </Box>
      )}

      {/* Step navigation */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "flex-end",
          gap: 1,
          mt: 2,
        }}
      >
        {formStep < 1 ? (
          <Box
            sx={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
            }}
          >
            <Tooltip
              title={`Supervised converters will include this column in their learning process.`}
              placement="top"
            >
              <IconButton>
                <HelpIcon />
              </IconButton>
            </Tooltip>
            <ConverterClassColumnModal
              updateClassColumn={setClassColumnInitialValue}
              classColumnInitialValue={classColumnInitialValue}
              notebook={notebook}
            />
            <Button
              variant="contained"
              disabled={classColumnInitialValue === null}
              onClick={() => setFormStep((s) => s + 1)}
            >
              Next
            </Button>
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
