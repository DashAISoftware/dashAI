import { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Autocomplete,
  TextField,
  Typography,
} from "@mui/material";
import FormSchema from "../../../../components/shared/FormSchema";
import FormSchemaContainer from "../../../../components/shared/FormSchemaContainer";
import { getGeneratorComponents } from "../../../../api/rag";
import {
  buildDefaultValuesFromSchemaProperties,
  getInitialModelParameters,
} from "../components/ragFormDefaults";

export default function GeneratorConfigurationStep({
  generatorModel,
  setGeneratorModel,
  setNextEnabled,
}) {
  const [generators, setGenerators] = useState([]);
  const [selectedGenerator, setSelectedGenerator] = useState(null);

  const formInitialValues = useMemo(
    () =>
      getInitialModelParameters({
        selectedModel: selectedGenerator,
        currentModelName: generatorModel?.component,
        currentParams: generatorModel?.params,
      }),
    [selectedGenerator, generatorModel?.component, generatorModel?.params],
  );

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      const data = await getGeneratorComponents();
      if (isMounted) setGenerators(data || []);
    };
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  // if parent gives a preselected generator, sync it
  useEffect(() => {
    if (!generators.length) return;
    if (generatorModel?.component) {
      const found = generators.find((g) => g.name === generatorModel.component);
      if (found) setSelectedGenerator(found);
    }
    // enable next when there is a selection
    setNextEnabled(!!generatorModel?.component);
  }, [generators, generatorModel?.component]);

  const handleSelection = (event, newValue) => {
    setSelectedGenerator(newValue);
    if (newValue) {
      setGeneratorModel({
        component: newValue.name,
        params: buildDefaultValuesFromSchemaProperties(
          newValue.schema?.properties || {},
        ),
      });
      setNextEnabled(true);
    } else {
      setGeneratorModel({ component: "", params: {} });
      setNextEnabled(false);
    }
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <Typography variant="subtitle2" sx={{ mb: 0 }}>
        Configure Generator Model (LLM)
      </Typography>

      <Autocomplete
        disablePortal
        options={generators}
        getOptionLabel={(option) => option.name}
        value={selectedGenerator}
        onChange={handleSelection}
        isOptionEqualToValue={(option, value) => option.name === value?.name}
        renderInput={(params) => (
          <TextField {...params} label="Generator Model" />
        )}
      />

      {selectedGenerator && (
        <FormSchemaContainer key={`generator-form-${selectedGenerator.name}`}>
          <FormSchema
            autoSave
            model={selectedGenerator.name}
            initialValues={formInitialValues}
            onFormSubmit={(values) => {
              setGeneratorModel({
                component: selectedGenerator.name,
                params: values,
              });
            }}
            setError={(err) => console.error("FormSchema error:", err)}
            hideButtons
          />
        </FormSchemaContainer>
      )}
    </Box>
  );
}

GeneratorConfigurationStep.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func,
};
