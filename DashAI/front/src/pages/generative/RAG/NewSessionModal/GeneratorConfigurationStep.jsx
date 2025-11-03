import { useState, useEffect, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Autocomplete,
  TextField,
  Typography,
  Button,
} from "@mui/material";
import { useFormik } from "formik";
import FormSchemaRenderFields from "../../../../components/shared/FormSchemaRenderFields";
import FormSchemaContainer from "../../../../components/shared/FormSchemaContainer";
import FormSchemaDialog from "../../../../components/shared/FormSchemaDialog";
import FormSchema from "../../../../components/shared/FormSchema";
import { getGeneratorComponents } from "../../../../api/rag";
import {
  preprocessSchema,
  buildYupSchema,
} from "../../../../components/generative/utils";
import { useFormSchemaStore } from "../../../../contexts/schema";

export default function GeneratorConfigurationStep({
  generatorModel,
  setGeneratorModel,
  setNextEnabled,
}) {
  return (
    <FormSchemaContainer>
      <GeneratorConfigurationContent
        generatorModel={generatorModel}
        setGeneratorModel={setGeneratorModel}
        setNextEnabled={setNextEnabled}
      />
    </FormSchemaContainer>
  );
}

function GeneratorConfigurationContent({
  generatorModel,
  setGeneratorModel,
  setNextEnabled,
}) {
  const [generators, setGenerators] = useState([]);
  const [currentSelectedGeneratorOption, setCurrentSelectedGeneratorOption] =
    useState(null);
  const [validationSchema, setValidationSchema] = useState(null);
  const [openConfigModal, setOpenConfigModal] = useState(false);
  const [subModelToConfig, setSubModelToConfig] = useState(null);

  const { properties } = useFormSchemaStore();

  useEffect(() => {
    if (properties.length > 0) {
      const lastProperty = properties[properties.length - 1];
      setSubModelToConfig(lastProperty.label);
      setOpenConfigModal(true);
    }
  }, [properties]);

  const getInitialParamsFromSchema = useCallback((schemaProperties) => {
    if (!schemaProperties) return {};
    return Object.keys(schemaProperties).reduce((acc, key) => {
      acc[key] =
        schemaProperties[key].placeholder !== undefined
          ? schemaProperties[key].placeholder
          : "";
      return acc;
    }, {});
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loadGenerators = async () => {
      const data = await getGeneratorComponents();
      if (isMounted) setGenerators(data);
    };
    loadGenerators();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!generators.length || !generatorModel?.component) return;
    const existingGenerator = generators.find(
      (r) => r.name === generatorModel.component,
    );
    if (existingGenerator) {
      setCurrentSelectedGeneratorOption(existingGenerator);
      if (
        generatorModel.params &&
        JSON.stringify(formik.values) !== JSON.stringify(generatorModel.params)
      ) {
        formik.setValues(generatorModel.params);
      }
    }
  }, [generators, generatorModel?.component, generatorModel?.params]);

  const formik = useFormik({
    initialValues: generatorModel?.params || {},
    validationSchema: validationSchema,
    enableReinitialize: true,
    onSubmit: (values) => {},
  });

  useEffect(() => {
    const generatorSchemaProperties =
      currentSelectedGeneratorOption?.schema?.properties;

    if (generatorSchemaProperties) {
      const processedProps = preprocessSchema(generatorSchemaProperties);
      setValidationSchema(buildYupSchema(processedProps));

      const initialFormValues = Object.keys(processedProps).reduce(
        (acc, key) => {
          acc[key] =
            generatorModel?.params?.[key] !== undefined
              ? generatorModel.params[key]
              : processedProps[key].placeholder !== undefined
                ? processedProps[key].placeholder
                : "";
          return acc;
        },
        {},
      );
      formik.setValues(initialFormValues);
    } else {
      setValidationSchema(null);
      formik.setValues({});
    }
  }, [currentSelectedGeneratorOption, generatorModel?.params]);

  useEffect(() => {
    const isValid = !!currentSelectedGeneratorOption && formik.isValid;
    setNextEnabled(isValid);
  }, [currentSelectedGeneratorOption, formik.isValid, setNextEnabled]);

  const handleGeneratorSelectionChange = (event, newValue) => {
    setCurrentSelectedGeneratorOption(newValue);

    if (newValue) {
      const initialParameters = getInitialParamsFromSchema(
        newValue.schema?.properties,
      );
      const modelData = {
        component: newValue.name,
        params: initialParameters,
      };
      setGeneratorModel(modelData);
    } else {
      setGeneratorModel({ component: "", params: {} });
    }
  };

  const handleParametersChange = (updatedValues) => {
    formik.setValues((prevValues) => ({
      ...prevValues,
      ...updatedValues,
    }));

    const modelData = {
      component: currentSelectedGeneratorOption.name,
      params: {
        ...formik.values,
        ...updatedValues,
      },
    };
    setGeneratorModel(modelData);
  };

  const processedProperties = currentSelectedGeneratorOption?.schema?.properties
    ? preprocessSchema(currentSelectedGeneratorOption.schema.properties)
    : {};

  return (
    <Box
      display={"flex"}
      height={"100%"}
      width={"100%"}
      flexDirection={"column"}
      justifyContent={"flex-start"}
      overflow={"auto"}
    >
      <Typography
        sx={{
          fontSize: "16px",
          whiteSpace: "normal",
          wordBreak: "break-word",
          mb: 2,
        }}
      >
        Configure Generator Model (LLM)
      </Typography>

      <Autocomplete
        disablePortal
        options={generators}
        getOptionLabel={(option) => option.name}
        value={currentSelectedGeneratorOption}
        onChange={handleGeneratorSelectionChange}
        isOptionEqualToValue={(option, value) => option.name === value?.name}
        renderInput={(params) => (
          <TextField {...params} label="Generator Model" />
        )}
        sx={{ mb: 3 }}
      />

      {currentSelectedGeneratorOption &&
        currentSelectedGeneratorOption.schema && (
          <form onSubmit={formik.handleSubmit}>
            <Box width="100%">
              <Typography
                sx={{
                  fontSize: "16px",
                  whiteSpace: "normal",
                  wordBreak: "break-word",
                  mb: 2,
                }}
              >
                Parameters
              </Typography>
              <FormSchemaRenderFields
                modelSchema={processedProperties}
                formik={formik}
                autoSave={false}
                handleUpdateSchema={handleParametersChange}
                onFormSubmit={formik.handleSubmit}
                setError={(error) =>
                  console.error("FormSchemaRenderFields Error:", error)
                }
                errorsMessage={formik.errors}
              />
            </Box>
          </form>
        )}

      {/* Configuration Modal for sub-models */}
      {openConfigModal && subModelToConfig && (
        <FormSchemaDialog
          modelToConfigure={subModelToConfig}
          open={openConfigModal}
          setOpen={setOpenConfigModal}
          onFormSubmit={(values) => {
            setOpenConfigModal(false);
          }}
        >
          <FormSchema
            model={subModelToConfig}
            initialValues={{}}
            onFormSubmit={(values) => {
              setOpenConfigModal(false);
            }}
            onCancel={() => setOpenConfigModal(false)}
          />
        </FormSchemaDialog>
      )}
    </Box>
  );
}

GeneratorConfigurationContent.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

GeneratorConfigurationStep.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};
