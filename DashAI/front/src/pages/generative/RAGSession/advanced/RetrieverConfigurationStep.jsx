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
import { getRetrievalParadigm, getRetrieverComponents } from "../../../../api/rag";
import FormSchema from "../../../../components/shared/FormSchema";
import CompositeRetrieverBuilder from "./CompositeRetrieverBuilder";
import {
  FormSchemaProvider,
} from "../../../../contexts/schema";
import { resolveDefaults } from "../../../../utils/schema";

/** Parent class name for all dense embedding components in the backend ComponentRegistry. */
const DENSE_EMBEDDING_PARENT = "DenseEmbedding";

const COMPOSITE_NAMES = ["SequentialRetriever", "ParallelRetriever", "MMRRerankerRetriever"];

function getDisplayName(component) {
  if (!component) return "";
  const dn = component.display_name;
  if (!dn) return component.name || "";
  if (typeof dn === "string") return dn;
  if (dn.en) return dn.en;
  if (dn.es) return dn.es;
  // Fallback: try any available language key
  const keys = Object.keys(dn);
  for (const key of keys) {
    if (typeof dn[key] === "string") return dn[key];
  }
  return component.name || "";
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
    const retrieversRef = useRef([]);

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
        let retrievers = [];
        let concreteEmbeddings = [];
        try {
          const results = await Promise.all([
            getRetrievalParadigm(),
            getRetrieverComponents(DENSE_EMBEDDING_PARENT),
          ]);
          retrievers = results[0] || [];
          concreteEmbeddings = (results[1] || []).filter(
            (c) => !(c.flags || []).includes("abstract"),
          );
        } catch (e) {
          retrievers = await getRetrievalParadigm();
        }
        retrieversRef.current = retrievers;

        const keywordOptions = retrievers
          .filter((c) => (c.flags || []).includes("keyword"))
          .map((c) => ({ ...c, _type: "retriever" }));
        const denseOptions = concreteEmbeddings.map((c) => ({
          ...c,
          _type: "embedding",
        }));
        const compositeOptions = retrievers
          .filter((c) => (c.flags || []).includes("composite"))
          .map((c) => ({ ...c, _type: "retriever" }));
        const merged = [
          ...keywordOptions,
          ...denseOptions,
          ...compositeOptions,
        ];
        setAllOptions(merged);

        if (retrieverModel?.component) {
          let found = null;
          if (retrieverModel.component === "DenseEmbeddingRetriever") {
            const embName =
              retrieverModel.params?.embedding_model?.component;
            if (embName) {
              found = merged.find((c) => c.name === embName);
            }
            if (!found) {
              found =
                retrievers.find(
                  (c) => c.name === "DenseEmbeddingRetriever",
                ) || null;
            }
          } else {
            found = merged.find((c) => c.name === retrieverModel.component);
            if (!found && allParadigms) {
              found = allParadigms.find(
                (c) => c.name === retrieverModel.component,
              );
            }
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

    const handleRetrieverChange = useCallback(async (_event, newValue) => {
      savedParamsRef.current = null;

      if (!newValue) {
        setSelectedRetriever(null);
        setRetrieverModel({ component: "", params: {} });
        setOpenConfig(false);
        setNextEnabled(false);
        return;
      }

      if (newValue._type === "embedding") {
        const embeddingDefaults = await resolveDefaults(newValue.name);
        const denseRetrieverDefaults = await resolveDefaults(
          "DenseEmbeddingRetriever",
        );
        const model = {
          component: "DenseEmbeddingRetriever",
          params: {
            ...denseRetrieverDefaults,
            embedding_model: {
              component: newValue.name,
              params: embeddingDefaults,
            },
          },
        };
        const found = retrieversRef.current.find(
          (c) => c.name === "DenseEmbeddingRetriever",
        );
        setSelectedRetriever(
          found
            ? { ...found, _type: "retriever" }
            : { ...newValue, _type: "retriever", name: "DenseEmbeddingRetriever" },
        );
        setRetrieverModel(model);
        setOpenConfig(Boolean(found?.schema?.properties));
        setNextEnabled(true);
      } else {
        const defaults = await resolveDefaults(newValue.name);
        setSelectedRetriever(newValue);
        setRetrieverModel({ component: newValue.name, params: defaults });
        setOpenConfig(Boolean(newValue?.schema?.properties));
        setNextEnabled(true);
      }
    }, [setRetrieverModel, setNextEnabled]);

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

    const isComposite =
      selectedRetriever && COMPOSITE_NAMES.includes(selectedRetriever.name);

    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3, p: 2 }}>
        <Typography variant="subtitle2" sx={{ mb: 0 }}>
          {t("generative:rag.composite.selectModel")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {t("generative:rag.composite.retrieverDescription")}
        </Typography>
        <Autocomplete
          options={allOptions}
          getOptionLabel={(opt) => getDisplayName(opt)}
          groupBy={(opt) => {
            if (opt._type === "embedding")
              return t("generative:rag.composite.denseGroup");
            const flags = opt.flags || [];
            if (flags.includes("composite"))
              return t("generative:rag.composite.compositeGroup");
            if (flags.includes("keyword"))
              return t("generative:rag.composite.keywordGroup");
            return t("generative:rag.composite.simpleGroup");
          }}
          value={selectedRetriever}
          onChange={handleRetrieverChange}
          isOptionEqualToValue={(a, b) => a.name === b.name}
          renderInput={(params) => (
            <TextField {...params} label={t("generative:rag.retrieverConfig.modelLabel")} />
          )}
        />

        {selectedRetriever && openConfig && !isComposite && (
          <FormSchemaProvider
            key={`retriever-provider-${selectedRetriever.name}`}
          >
            <AutoSaveFormSchema
              key={`retriever-form-${selectedRetriever.name}`}
              selectedRetriever={selectedRetriever}
              retrieverModel={retrieverModel}
              onParametersChange={handleParametersSave}
            />
          </FormSchemaProvider>
        )}

        {selectedRetriever && openConfig && isComposite && (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mt: -1 }}>
              {t("generative:rag.composite.compositeInstructions")}
            </Typography>
            <CompositeRetrieverBuilder
              key={`composite-${selectedRetriever.name}`}
              rootComponent={selectedRetriever.name}
              rootParams={retrieverModel.params}
              onChange={handleCompositeChange}
            />
          </>
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
