import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Button,
  CircularProgress,
  FormControlLabel,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import PresetCardList from "./PresetCardList";
import QueryTransformationAdvancedModal from "../../../pages/generative/RAGSession/advanced/QueryTransformationAdvancedModal";
import {
  getGeneratorComponents,
  getQueryTransformationComponents,
  getQueryTransformationPrompts,
} from "../../../api/rag";
import {
  isCompleteQueryTransformationRef,
  resolveDefaultGeneratorName,
  resolveEnableGenerator,
  resolveLabel,
} from "../../../utils/ragQueryTransformation";

/**
 * The message of a failed option request, preferring the API's detail.
 * @param {object} error - The rejection raised by the request.
 * @returns {string} A renderable reason.
 */
function loadFailureReason(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  return error?.message ?? String(error);
}

/**
 * Build the `{component, params}` reference a freshly enabled stage PUTs.
 *
 * The backend fills omitted defaults server-side, but it validates that
 * `llm_model` and `prompt` are present, so both are seeded here: the generator
 * the caller resolved (a downloaded model, see `resolveEnableGenerator`)
 * and the technique's default prompt. Everything else, the optional reranker
 * included, is left out so the server supplies its default.
 *
 * @param {object} transformerComponent - The transformer component to enable.
 * @param {string} technique - Its `metadata.technique`, to pick the prompt.
 * @param {object|null} generator - The generator to seed, if any.
 * @param {Array} prompts - The transformation prompts to choose from.
 * @returns {object} The `{component, params}` session parameter value.
 */
export function buildQueryTransformationRef(
  transformerComponent,
  technique,
  generator,
  prompts,
) {
  const params = {};
  if (generator) {
    params.llm_model = { component: generator.name, params: {} };
  }
  const defaultPrompt = (prompts || []).find(
    (prompt) =>
      prompt.metadata?.technique === technique &&
      prompt.metadata?.variant === "default",
  );
  if (defaultPrompt) {
    params.prompt = {
      component: defaultPrompt.name,
      params: { language: "en" },
    };
  }
  return { component: transformerComponent.name, params };
}

/**
 * The optional query transformation stage, edited as a `{component, params}`
 * reference or `null` when disabled.
 *
 * Wears the retrieval card's shape: a technique card list over the resolution
 * API, with an advanced modal for the full reference. It owns its own option
 * loading so the panel only has to wire the section.
 *
 * @param {object}   props
 * @param {object|null} props.value - The current stage ref, or null when off.
 * @param {Function} props.onChange - Sets the stage ref, or null to disable.
 * @param {object}   [props.section] - The resolved configuration section, for
 *   the registration notice.
 * @returns {JSX.Element} The query transformation picker.
 */
export default function QueryTransformationPicker({
  value,
  onChange,
  section,
}) {
  const { t } = useTranslation(["generative"]);
  const [transformers, setTransformers] = useState([]);
  const [generators, setGenerators] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [loadingTransformers, setLoadingTransformers] = useState(true);
  const [loadingPrompts, setLoadingPrompts] = useState(true);
  const [loadingGenerators, setLoadingGenerators] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [blockMessage, setBlockMessage] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const loading = loadingTransformers || loadingPrompts || loadingGenerators;

  useEffect(() => {
    const recordFailure = (error) =>
      setLoadError((previous) => previous ?? loadFailureReason(error));

    getQueryTransformationComponents()
      .then((data) => setTransformers(data || []))
      .catch((error) => {
        console.error("Failed to load query transformers:", error);
        recordFailure(error);
      })
      .finally(() => setLoadingTransformers(false));
    getQueryTransformationPrompts()
      .then((data) => setPrompts(data || []))
      .catch((error) => {
        console.error("Failed to load query transformation prompts:", error);
        recordFailure(error);
      })
      .finally(() => setLoadingPrompts(false));
    getGeneratorComponents()
      .then((data) => setGenerators(data || []))
      .catch((error) => {
        console.error("Failed to load generation models:", error);
        recordFailure(error);
      })
      .finally(() => setLoadingGenerators(false));
  }, []);

  const enabled = value != null;

  // The backend-declared default generator (the transformer schemas'
  // `llm_model` placeholder). Enabling seeds a downloaded model, preferring
  // this default: see `resolveEnableGenerator`.
  const defaultGeneratorName = useMemo(
    () => resolveDefaultGeneratorName(transformers),
    [transformers],
  );

  const technique = useMemo(
    () =>
      transformers.find((component) => component.name === value?.component)
        ?.metadata?.technique,
    [transformers, value?.component],
  );

  // The card list is per-technique, so a card is matched on the component
  // alone: its `params` carry server-filled defaults that always differ from
  // the `{}` a card seeds.
  const presets = useMemo(
    () =>
      transformers.map((component) => ({
        key: component.name,
        display_name: resolveLabel(component.display_name, component.name),
        description: resolveLabel(component.description),
        component: component.name,
        params: {},
      })),
    [transformers],
  );

  // Enabling never persists a ref without a downloaded model and a prompt:
  // the backend rejects both with an unexplained 400/409 otherwise.
  const enableWith = (transformer) => {
    if (loading || loadError) return;
    const generator = resolveEnableGenerator(generators, defaultGeneratorName);
    if (!generator) {
      setBlockMessage(
        t("generative:rag.config.queryTransformation.needsDownloadedModel"),
      );
      return;
    }
    const ref = buildQueryTransformationRef(
      transformer,
      transformer?.metadata?.technique,
      generator,
      prompts,
    );
    if (!isCompleteQueryTransformationRef(ref)) {
      setBlockMessage(
        t("generative:rag.config.queryTransformation.promptRequired"),
      );
      return;
    }
    setBlockMessage(null);
    onChange(ref);
  };

  // The advanced modal may only persist a complete ref; an incomplete one is
  // refused here as well as by its disabled Done button.
  const commitStage = (ref) => {
    if (ref && !isCompleteQueryTransformationRef(ref)) return;
    onChange(ref);
  };

  const handleSelect = (preset) => {
    const transformer =
      transformers.find((component) => component.name === preset.component) ||
      preset;
    enableWith(transformer);
  };

  // An enabled component the registry does not know about: the saved section
  // reports it unregistered, and a freshly chosen one is absent from the list.
  const unregistered =
    enabled &&
    section?.registered !== true &&
    !transformers.some((component) => component.name === value?.component);

  // Turning a stage off never depends on the option loads: the switch is only
  // held disabled while enabling one, which needs the loaded options.
  return (
    <Stack spacing={1.5}>
      <FormControlLabel
        control={
          <Switch
            size="small"
            checked={enabled}
            disabled={
              !enabled &&
              (loading || Boolean(loadError) || transformers.length === 0)
            }
            onChange={(event) =>
              event.target.checked
                ? enableWith(transformers[0])
                : onChange(null)
            }
          />
        }
        label={t("generative:rag.config.queryTransformation.enable")}
      />

      {loading && (
        <Stack direction="row" spacing={1} alignItems="center">
          <CircularProgress size={14} />
          <Typography variant="caption" color="text.secondary">
            {t("common:loading")}
          </Typography>
        </Stack>
      )}

      {loadError && (
        <Alert severity="error" sx={{ py: 0.5 }}>
          {t("generative:rag.config.queryTransformation.loadFailed", {
            reason: loadError,
          })}
        </Alert>
      )}

      {blockMessage && !loading && !loadError && (
        <Alert severity="warning" sx={{ py: 0.5 }}>
          {blockMessage}
        </Alert>
      )}

      {!loading && !loadError && transformers.length === 0 && (
        <Typography variant="caption" color="text.secondary">
          {t("generative:rag.config.queryTransformation.noneAvailable")}
        </Typography>
      )}

      <PresetCardList
        presets={presets}
        activeKey={enabled ? value?.component : null}
        onSelect={handleSelect}
      />

      {unregistered && (
        <Alert severity="info" sx={{ py: 0.5 }}>
          {value?.component}:{" "}
          {t("generative:rag.config.queryTransformation.unknownComponent")}
        </Alert>
      )}

      <Button
        variant="outlined"
        size="small"
        sx={{ alignSelf: "flex-start" }}
        disabled={!enabled}
        onClick={() => setShowAdvanced(true)}
      >
        {t("generative:rag.config.queryTransformation.advanced")}
      </Button>

      <QueryTransformationAdvancedModal
        open={showAdvanced}
        onClose={() => setShowAdvanced(false)}
        model={value}
        setModel={commitStage}
        technique={technique}
        generators={generators}
      />
    </Stack>
  );
}

QueryTransformationPicker.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func.isRequired,
  section: PropTypes.object,
};
