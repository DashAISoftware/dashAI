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
import { getGeneratorComponents } from "../../../../api/rag";
import {
  preprocessSchema,
  buildYupSchema,
} from "../../../../components/generative/utils";

export default function GeneratorConfigurationStep({
  generatorModel,
  setGeneratorModel,
  setNextEnabled,
}) {
  const [generators, setGenerators] = useState([]);
  const [currentSelectedGeneratorOption, setCurrentSelectedGeneratorOption] =
    useState(null);
  const [validationSchema, setValidationSchema] = useState(null);

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
    const loadAndSetGenerator = async () => {
      const data = await getGeneratorComponents();
      setGenerators(data);

      if (generatorModel?.name) {
        const existingGenerator = data.find(
          (r) => r.name === generatorModel.name,
        );
        if (existingGenerator) {
          setCurrentSelectedGeneratorOption(existingGenerator);
        }
      }
    };
    loadAndSetGenerator();
  }, [generatorModel?.name]);

  const formik = useFormik({
    initialValues: generatorModel?.parameters || {},
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
            generatorModel?.parameters?.[key] !== undefined
              ? generatorModel.parameters[key]
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
  }, [currentSelectedGeneratorOption, generatorModel?.parameters]);

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
      setGeneratorModel({
        name: newValue.name,
        parameters: initialParameters,
      });
    } else {
      setGeneratorModel({ name: "", parameters: {} });
    }
  };

  const handleParametersChange = (updatedValues) => {
    formik.setValues((prevValues) => ({
      ...prevValues,
      ...updatedValues,
    }));

    setGeneratorModel({
      name: currentSelectedGeneratorOption.name,
      parameters: {
        ...formik.values,
        ...updatedValues,
      },
    });
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
    </Box>
  );
}
