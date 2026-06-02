import {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
  forwardRef,
  useImperativeHandle,
} from "react";
import PropTypes from "prop-types";
import { Box, Autocomplete, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { getRetrievalParadigm } from "../../../../api/rag";
import FormSchema from "../../../../components/shared/FormSchema";
import CompositeRetrieverBuilder from "./CompositeRetrieverBuilder";
import {
  FormSchemaProvider,
} from "../../../../contexts/schema";
import { resolveDefaults } from "../../../../utils/schema";

const COMPOSITE_NAMES = ["SequentialRetriever", "ParallelRetriever"];

function getDisplayName(component) {
  if (!component) return "";
  const dn = component.display_name;
  if (!dn) return component.name || "";
  if (typeof dn === "string") return dn;
  if (dn.en) return dn.en;
  if (dn.es) return dn.es;
  return String(dn);
}

function getGroupNameForStep(component, t) {
  if (COMPOSITE_NAMES.includes(component.name)) {
    return t("generative:simplifiedRag.composite.compositeGroup");
  }
  const name = component.name || "";
  if (name.includes("TFIDF") || name.includes("BM25")) {
    return t("generative:simplifiedRag.composite.keywordGroup");
  }
  if (name.endsWith("DenseRetriever")) {
    return t("generative:simplifiedRag.composite.embeddingGroup");
  }
  return t("generative:simplifiedRag.composite.simpleGroup");
}

function AutoSaveFormSchema({
  selectedRetriever,
  retrieverModel,
  onParametersChange,
}) {
  const formikRef = useRef(null);

  const [fetchedDefaults, setFetchedDefaults] = useState(null);

  useEffect(() => {
    if (!selectedRetriever) return;
    let cancelled = false;
    (async () => {
      const d = await resolveDefaults(selectedRetriever.name);
      if (!cancelled) setFetchedDefaults(d);
    })();
    return () => { cancelled = true; };
  }, [selectedRetriever]);

  const initialValues = useMemo(() => {
    if (
      retrieverModel?.component === selectedRetriever?.name &&
      retrieverModel?.params &&
      Object.keys(retrieverModel.params).length > 0
    ) {
      return retrieverModel.params;
    }
    return fetchedDefaults || {};
  }, [selectedRetriever, retrieverModel, fetchedDefaults]);

  const handleFormSubmit = useCallback(
    (values) => {
      onParametersChange(values);
    },
    [onParametersChange],
  );

  return (
    <FormSchema
      model={selectedRetriever.name}
      initialValues={initialValues}
      autoSave={true}
      onFormSubmit={handleFormSubmit}
      formSubmitRef={formikRef}
      hideButtons
    />
  );
}

const RetrieverConfigurationStep = forwardRef(
  function RetrieverConfigurationStep(
    { allParadigms, retrieverModel, setRetrieverModel, setNextEnabled },
    ref,
  ) {
    const { t } = useTranslation(["generative"]);
    const [allOptions, setAllOptions] = useState([]);
    const [selectedRetriever, setSelectedRetriever] = useState(null);
    const [openConfig, setOpenConfig] = useState(false);
    const savedParamsRef = useRef(null);

    const saveCurrentFormValues = useCallback(() => {
      const values = savedParamsRef.current;
      if (values && Object.keys(values).length > 0 && selectedRetriever) {
        setRetrieverModel({
          component: selectedRetriever.name,
          params: values,
        });
      }
    }, [selectedRetriever, setRetrieverModel]);

    useEffect(() => {
      return () => {
        saveCurrentFormValues();
      };
    }, [saveCurrentFormValues]);

    useImperativeHandle(
      ref,
      () => ({ saveFormValues: saveCurrentFormValues }),
      [saveCurrentFormValues],
    );

    useEffect(() => {
      const load = async () => {
        const fetched = await getRetrievalParadigm();
        setAllOptions(fetched);

        if (retrieverModel?.component) {
          let found = fetched.find((c) => c.name === retrieverModel.component);
          if (!found && allParadigms) {
            found = allParadigms.find((c) => c.name === retrieverModel.component);
          }
          if (found) {
            setSelectedRetriever(found);
            setOpenConfig(true);
            setNextEnabled(true);
          }
        }
      };
      load();
    }, []);

    const handleRetrieverChange = async (_event, newValue) => {
      setSelectedRetriever(newValue);
      savedParamsRef.current = null;

      if (newValue) {
        const defaults = await resolveDefaults(newValue.name);
        setRetrieverModel({ component: newValue.name, params: defaults });
        setOpenConfig(Boolean(newValue?.schema?.properties));
        setNextEnabled(true);
      } else {
        setRetrieverModel({ component: "", params: {} });
        setOpenConfig(false);
        setNextEnabled(false);
      }
    };

    const handleParametersSave = useCallback(
      (newParams) => {
        savedParamsRef.current = newParams;
        setRetrieverModel({
          component: selectedRetriever?.name || "",
          params: newParams,
        });
        setNextEnabled(true);
      },
      [selectedRetriever?.name, setRetrieverModel, setNextEnabled],
    );

    const handleCompositeChange = useCallback(
      (updated) => {
        savedParamsRef.current = updated.params;
        setRetrieverModel({
          component: updated.component,
          params: updated.params,
        });
        setNextEnabled(true);
      },
      [setRetrieverModel, setNextEnabled],
    );

    const isComposite = selectedRetriever && COMPOSITE_NAMES.includes(selectedRetriever.name);

    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3, p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 0 }}>
          Select retriever model
        </Typography>
        <Autocomplete
          disablePortal
          options={allOptions}
          getOptionLabel={(opt) => getDisplayName(opt)}
          groupBy={(opt) => getGroupNameForStep(opt, t)}
          value={selectedRetriever}
          onChange={handleRetrieverChange}
          isOptionEqualToValue={(a, b) => a.name === b.name}
          renderInput={(params) => (
            <TextField {...params} label="Retriever model" />
          )}
        />

        {selectedRetriever && openConfig && !isComposite && (
          <FormSchemaProvider key={`retriever-provider-${selectedRetriever.name}`}>
            <AutoSaveFormSchema
              key={`retriever-form-${selectedRetriever.name}`}
              selectedRetriever={selectedRetriever}
              retrieverModel={retrieverModel}
              onParametersChange={handleParametersSave}
            />
          </FormSchemaProvider>
        )}

        {selectedRetriever && openConfig && isComposite && (
          <CompositeRetrieverBuilder
            key={`composite-${selectedRetriever.name}`}
            rootComponent={selectedRetriever.name}
            rootParams={retrieverModel.params}
            onChange={handleCompositeChange}
          />
        )}
      </Box>
    );
  },
);

RetrieverConfigurationStep.propTypes = {
  allParadigms: PropTypes.array,
  retrieverModel: PropTypes.object,
  setRetrieverModel: PropTypes.func.isRequired,
  setNextEnabled: PropTypes.func.isRequired,
};

export default RetrieverConfigurationStep;
