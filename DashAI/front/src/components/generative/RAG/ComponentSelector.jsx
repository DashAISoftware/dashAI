import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  CircularProgress
} from "@mui/material";
import FormSchemaRenderFields from "../../shared/FormSchemaRenderFields";
import { useFormik } from "formik";
import { preprocessSchema, buildYupSchema } from "../utils";
import { getRelatedComponents } from "../../../api/generativeTask";
function ComponentSelector({
  componentType,
  fetchComponents,
  initialValues,
  onConfigurationChange,
  setNextEnabled
}) {
  const [components, setComponents] = useState([]);
  const [selectedComponent, setSelectedComponent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [validationSchema, setValidationSchema] = useState(null);

  try {
    console.log(getRelatedComponents("TextToTextGenerationTask"));
  } catch (error) {
  }



  // Fetch available components
  useEffect(() => {
    const getComponents = async () => {
      setLoading(true);
      try {
        const data = await fetchComponents();
        setComponents(data);
        
        // If we have initialValues with a model_name, select that component
        if (initialValues?.model_name) {
          const preselectedComponent = data.find(c => c.name === initialValues.model_name);
          if (preselectedComponent) {
            setSelectedComponent(preselectedComponent);
          }
        } else {
          console.warn(`No initial model_name provided for ${componentType} selection.`);
        }
      } catch (error) {
        console.error(`Error fetching ${componentType} components:`, error);
      } finally {
        setLoading(false);
      }
    };
    
    getComponents();
  }, [componentType, fetchComponents]);

  // Set up form validation schema when component changes
  useEffect(() => {
    if (selectedComponent?.schema?.properties) {
      const processedProps = preprocessSchema(selectedComponent.schema.properties);
      setValidationSchema(buildYupSchema(processedProps));
      console.log("Processed properties for form:", processedProps);
      // Merge any existing values with defaults from schema
      const schemaDefaults = Object.keys(processedProps).reduce(
        (acc, key) => {
          acc[key] = processedProps[key].placeholder || "";
          console.log(`Setting default for ${key}:`, acc[key]);
          return acc;
        }, 
        { name: "", description: ""});
      
      // Preserve any values that were already set
      const mergedValues = {
        ...schemaDefaults,
        ...(initialValues?.parameters || {})
      };
      
      formik.setValues(mergedValues);
    }
  }, [selectedComponent]);

  const formik = useFormik({
    initialValues: initialValues?.parameters || {},
    validationSchema,
    enableReinitialize: true,
    onSubmit: (values) => {
      onConfigurationChange({
        model_name: selectedComponent.name,
        parameters: values
      });
    }
  });

  // Enable/disable next button based on form validity and selection
  useEffect(() => {
    if (selectedComponent && formik.isValid) {
      setNextEnabled(true);
      
      // Auto-submit valid values as they change
      if (formik.dirty) {
        onConfigurationChange({
          model_name: selectedComponent.name,
          parameters: formik.values
        });
      }
    } else {
      setNextEnabled(false);
    }
  }, [selectedComponent, formik.values, formik.isValid, formik.dirty]);

  // Process schema properties for the form renderer
  const processedProperties = selectedComponent?.schema?.properties
    ? preprocessSchema(selectedComponent.schema.properties)
    : {};

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Select {componentType}
      </Typography>
      
      {loading ? (
        <Box display="flex" justifyContent="center" my={4}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Autocomplete
            disablePortal
            options={components.map(c => c.name)}
            value={selectedComponent?.name || null}
            onChange={(_, newValue) => {
              const selected = components.find(c => c.name === newValue);
              setSelectedComponent(selected);
            }}
            renderInput={(params) => (
              <TextField {...params} label={`${componentType} Model`} />
            )}
            sx={{ mb: 4 }}
          />
          
          {selectedComponent && (
            <form onSubmit={formik.handleSubmit}>
              <Typography variant="subtitle1" gutterBottom>
                {selectedComponent.name} Configuration
              </Typography>
              
              <FormSchemaRenderFields
                modelSchema={processedProperties}
                formik={formik}
                autoSave={true}
                handleUpdateSchema={(updatedValues) => {
                  formik.setValues({...formik.values, ...updatedValues});
                }}
                onFormSubmit={formik.handleSubmit}
                setError={(error) => console.error(error)}
                errorsMessage={formik.errors}
              />
            </form>
          )}
        </>
      )}
    </Box>
  );
}

ComponentSelector.propTypes = {
  componentType: PropTypes.string.isRequired,
  fetchComponents: PropTypes.func.isRequired,
  initialValues: PropTypes.object,
  onConfigurationChange: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired
};

export default ComponentSelector;