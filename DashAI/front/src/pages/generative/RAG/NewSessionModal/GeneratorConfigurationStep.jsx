import { useState, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Autocomplete,
  TextField,
  Typography,
  Paper,
  Stack,
  DialogContentText,
} from "@mui/material";
import FormSchemaLayout from "../../../../components/shared/FormSchemaLayout";
import FormSchema from "../../../../components/shared/FormSchema";
import { getGeneratorComponents } from "../../../../api/rag";

/**
 * Simple generator configuration step that allows selecting a generator model
 * and editing its parameters via FormSchema.
 */
export default function GeneratorConfigurationStep({
  generatorModel,
  setGeneratorModel,
  setNextEnabled,
}) {
  const [generators, setGenerators] = useState([]);
  const [selectedGenerator, setSelectedGenerator] = useState(null);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generators, generatorModel?.component]);

  const handleSelection = (event, newValue) => {
    setSelectedGenerator(newValue);
    if (newValue) {
      // set initial params using placeholders if available
      const initialParams = Object.keys(
        newValue.schema?.properties || {},
      ).reduce((acc, k) => {
        acc[k] = newValue.schema.properties[k].placeholder ?? "";
        return acc;
      }, {});
      setGeneratorModel({
        component: newValue.name,
        params: generatorModel?.params ?? initialParams,
      });
      setNextEnabled(true);
    } else {
      setGeneratorModel({ component: "", params: {} });
      setNextEnabled(false);
    }
  };

  return (
    <Stack spacing={3} sx={{ height: "100%" }}>
      <DialogContentText>
        <Typography sx={{ fontSize: 16 }}>
          Configure Generator Model (LLM)
        </Typography>
      </DialogContentText>

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
        <FormSchemaLayout>
          <FormSchema
            autoSave
            model={selectedGenerator.name}
            initialValues={generatorModel?.params || {}}
            onFormSubmit={(values) => {
              setGeneratorModel({
                component: selectedGenerator.name,
                params: values,
              });
            }}
            setError={(err) => console.error("FormSchema error:", err)}
          />
        </FormSchemaLayout>
      )}
    </Stack>
  );
}

GeneratorConfigurationStep.propTypes = {
  generatorModel: PropTypes.object,
  setGeneratorModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func,
};
