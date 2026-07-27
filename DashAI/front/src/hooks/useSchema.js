import { useEffect, useState } from "react";
import { getComponents } from "../api/component";
import { formattedModel, generateYupSchema } from "../utils/schema";
import { useTranslation } from "react-i18next";

/**
 * This hook is used to get the schema of a model, it will return the schema and the initial values of the model
 * @param {string} modelName - The name of the model to get the schema
 */

// Formatted schemas rarely change mid-session (only a plugin install/restart
// would alter them), so cache by model name — multiple mounted callers asking
// for the same model (e.g. a dialog's own prefetch and the form it renders a
// step later) share one network round trip instead of each re-fetching from
// scratch, which previously showed an empty form for a beat every time.
const schemaCache = new Map();

export default function useSchema({ modelName = null } = {}) {
  const [model, setModel] = useState(() =>
    modelName ? (schemaCache.get(modelName) ?? null) : null,
  );
  const [loading, setLoading] = useState(false);
  const { t } = useTranslation();

  useEffect(() => {
    let cancelled = false;

    const cached = modelName ? schemaCache.get(modelName) : null;
    if (cached) {
      setModel(cached);
      return undefined;
    }

    setModel(null);

    const getModel = async () => {
      try {
        setLoading(true);
        const result = await getComponents({ model: modelName });
        const formattedSchema = await formattedModel(result?.schema);
        if (!cancelled) {
          schemaCache.set(modelName, formattedSchema);
          setModel(formattedSchema);
        }
      } catch (error) {
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    if (modelName) {
      getModel();
    }

    return () => {
      cancelled = true;
    };
  }, [modelName, t]);

  const { schema, initialValues } = model
    ? generateYupSchema(model)
    : { schema: {}, initialValues: {} };

  return {
    modelSchema: model,
    defaultValues: initialValues,
    yupSchema: schema,
    loading,
  };
}
