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
import { Alert, Box, Autocomplete, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { getRetrievalParadigm } from "../../../../api/rag";
import { retrieverCategory, sortByCategory } from "../retrieverKinds";
import { findChildrenField } from "../../../../components/shared/componentTree/componentTreeUtils";
import FormSchemaWithPrompts from "../../../../components/generative/RAG/FormSchemaWithPrompts";
import CompositeRetrieverBuilder from "./CompositeRetrieverBuilder";
import { FormSchemaProvider } from "../../../../contexts/schema";
import { resolveRetrieverDefaults } from "./resolveRetrieverDefaults";
import { EMPTY_COMPONENT_NAME } from "../../../../constants/rag";

/**
 * The message of a failed request or defect.
 * @param {*} error - The rejection or thrown value.
 * @returns {string} A renderable reason.
 */
function failureReason(error) {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Resolves a component's display name from its display_name field (string or multilingual).
 * @param {object} component - The component definition object.
 * @returns {string} The resolved display name or the component name as fallback.
 */
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

/**
 * Whether a retriever declares children, so its tree decides whether it can
 * be saved.
 * @param {object|null} retriever - The retriever component.
 * @returns {boolean} True for a composite retriever.
 */
function isCompositeRetriever(retriever) {
  return Boolean(findChildrenField(retriever?.schema));
}

/**
 * Auto-saving form wrapper around FormSchema for retriever parameter configuration.
 * Loads default values for the selected retriever and fires onParametersChange on edits.
 *
 * @param {object} props
 * @param {object} props.selectedRetriever - The currently selected retriever component.
 * @param {object} [props.retrieverModel] - The persisted retriever model { component, params }.
 * @param {function} props.onParametersChange - Callback with the latest parameter values.
 * @returns {JSX.Element} The auto-saving schema form.
 */
function AutoSaveFormSchema({
  selectedRetriever,
  retrieverModel,
  onParametersChange,
}) {
  const { t } = useTranslation(["common"]);
  const formikRef = useRef(null);

  const [fetchedDefaults, setFetchedDefaults] = useState(null);
  const [defaultsError, setDefaultsError] = useState(null);

  useEffect(() => {
    if (!selectedRetriever) return undefined;
    let cancelled = false;
    setDefaultsError(null);
    resolveRetrieverDefaults(selectedRetriever.name)
      .then((defaults) => {
        if (!cancelled) setFetchedDefaults(defaults);
      })
      .catch((error) => {
        if (!cancelled) setDefaultsError(failureReason(error));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedRetriever]);

  const storedParams = useMemo(() => {
    if (
      retrieverModel?.component === selectedRetriever?.name &&
      retrieverModel?.params &&
      Object.keys(retrieverModel.params).length > 0
    ) {
      return retrieverModel.params;
    }
    return null;
  }, [selectedRetriever, retrieverModel]);
  const initialValues = storedParams ?? fetchedDefaults;

  const handleFormSubmit = useCallback(
    (values) => {
      onParametersChange(values);
    },
    [onParametersChange],
  );

  if (defaultsError !== null && storedParams === null) {
    return (
      <Alert severity="error" sx={{ py: 0.5 }}>
        {t("common:componentTree.loadFailed", { reason: defaultsError })}
      </Alert>
    );
  }

  if (initialValues === null) return null;

  return (
    <FormSchemaWithPrompts
      model={selectedRetriever.name}
      initialValues={initialValues}
      autoSave
      onFormSubmit={handleFormSubmit}
      formSubmitRef={formikRef}
      hideButtons
    />
  );
}

/**
 * Step component for selecting and configuring a retriever (simple, dense embedding,
 * or composite). Exposes a `saveFormValues` imperative handle for parent dialogs.
 *
 * @param {object} props
 * @param {Array} [props.allParadigms] - All available retriever paradigms.
 * @param {object} [props.retrieverModel] - The current retriever model { component, params }.
 * @param {function} props.setRetrieverModel - State setter for the retriever model.
 * @param {function} props.setNextEnabled - Callback to enable/disable the next/submit button.
 * @param {object} ref - React ref for imperative handle (saveFormValues).
 * @returns {JSX.Element} The retriever configuration step UI.
 */
const RetrieverConfigurationStep = forwardRef(
  function RetrieverConfigurationStep(
    { allParadigms, retrieverModel, setRetrieverModel, setNextEnabled },
    ref,
  ) {
    const { t } = useTranslation(["generative", "common"]);
    const [allOptions, setAllOptions] = useState([]);
    const [selectedRetriever, setSelectedRetriever] = useState(null);
    const [openConfig, setOpenConfig] = useState(false);
    const [loadError, setLoadError] = useState(null);
    const savedRef = useRef(null);
    const changeRequestRef = useRef(0);

    /**
     * Persists the last edited configuration into the retriever model state.
     * The component is the one the saved params belong to, so a root swapped in
     * the tree is never stored with another component's name.
     * Used by parent dialogs via the imperative ref handle.
     */
    const saveCurrentFormValues = useCallback(() => {
      const saved = savedRef.current;
      if (saved && Object.keys(saved.params).length > 0) {
        setRetrieverModel({
          component: saved.component,
          params: saved.params,
        });
      }
    }, [setRetrieverModel]);

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
        let retrievers;
        try {
          retrievers = await getRetrievalParadigm();
        } catch (error) {
          setLoadError(failureReason(error));
          return;
        }
        const options = sortByCategory(
          retrievers.filter(
            (retriever) => retriever.configurable_object !== false,
          ),
          t("common:other"),
        );
        setAllOptions(options);

        if (retrieverModel?.component) {
          const found =
            options.find((c) => c.name === retrieverModel.component) ||
            allParadigms?.find((c) => c.name === retrieverModel.component) ||
            null;
          if (found) {
            setSelectedRetriever(found);
            setOpenConfig(true);
            setNextEnabled(!isCompositeRetriever(found));
          }
        }
      };
      load();
    }, []);

    /**
     * Handles selection of a new retriever from the autocomplete and resets
     * its parameters to the retriever's defaults.
     * @param {object} _event - The autocomplete event.
     * @param {object|null} newValue - The selected retriever option.
     */
    const handleRetrieverChange = useCallback(
      async (_event, newValue) => {
        savedRef.current = null;
        changeRequestRef.current += 1;
        const requestId = changeRequestRef.current;
        setLoadError(null);

        if (!newValue) {
          setSelectedRetriever(null);
          setRetrieverModel({ component: EMPTY_COMPONENT_NAME, params: {} });
          setOpenConfig(false);
          setNextEnabled(false);
          return;
        }

        let defaults;
        try {
          defaults = await resolveRetrieverDefaults(newValue.name);
        } catch (error) {
          if (requestId === changeRequestRef.current) {
            setLoadError(failureReason(error));
          }
          return;
        }
        if (requestId !== changeRequestRef.current) return;
        setSelectedRetriever(newValue);
        setRetrieverModel({ component: newValue.name, params: defaults });
        setOpenConfig(Boolean(newValue.schema?.properties));
        setNextEnabled(!isCompositeRetriever(newValue));
      },
      [setRetrieverModel, setNextEnabled],
    );

    /**
     * Stores updated parameter values from the auto-saving form into the retriever model.
     * @param {object} newParams - The latest parameter values from the form.
     */
    const handleParametersSave = useCallback(
      (newParams) => {
        savedRef.current = {
          component: selectedRetriever.name,
          params: newParams,
        };
        setRetrieverModel({
          component: selectedRetriever.name,
          params: newParams,
        });
        setNextEnabled(true);
      },
      [selectedRetriever, setRetrieverModel, setNextEnabled],
    );

    /**
     * Receives the serialised tree from CompositeRetrieverBuilder and persists it
     * into the retriever model. When the root was swapped for another component,
     * the selection follows it, so the selector and the saved model agree.
     * @param {object} updated - The updated composite model { component, params }.
     */
    const handleCompositeChange = useCallback(
      (updated) => {
        savedRef.current = {
          component: updated.component,
          params: updated.params,
        };
        setRetrieverModel({
          component: updated.component,
          params: updated.params,
        });
        if (updated.component !== selectedRetriever.name) {
          const swapped = allOptions.find(
            (option) => option.name === updated.component,
          );
          if (!swapped) {
            setLoadError(
              t("common:componentTree.unknownComponent", {
                component: updated.component,
              }),
            );
            return;
          }
          setSelectedRetriever(swapped);
        }
      },
      [allOptions, selectedRetriever, setRetrieverModel, t],
    );

    const isComposite = isCompositeRetriever(selectedRetriever);

    return (
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Typography
          variant="subtitle2"
          component="h3"
          sx={{ mb: 0, fontWeight: 600 }}
        >
          {t("generative:rag.composite.selectModel")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {t("generative:rag.composite.retrieverDescription")}
        </Typography>
        <Autocomplete
          options={allOptions}
          getOptionLabel={(opt) => getDisplayName(opt)}
          groupBy={(opt) => retrieverCategory(opt, t("common:other"))}
          value={selectedRetriever}
          onChange={handleRetrieverChange}
          isOptionEqualToValue={(a, b) => a.name === b.name}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("generative:rag.retrieverConfig.modelLabel")}
            />
          )}
        />

        {loadError !== null && (
          <Alert severity="error" sx={{ py: 0.5 }}>
            {t("common:componentTree.loadFailed", { reason: loadError })}
          </Alert>
        )}

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
              onValidityChange={setNextEnabled}
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
