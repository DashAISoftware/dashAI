import { useMemo, useState } from "react";
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
import useQueryTransformationOptions from "../../../hooks/useQueryTransformationOptions";
import {
  canPersistQueryTransformationRef,
  prepareEnableRef,
  resolveDefaultGeneratorName,
  resolveLabel,
} from "../../../utils/ragQueryTransformation";

/**
 * The optional query transformation stage, edited as a `{component, params}`
 * reference or `null` when disabled.
 *
 * Wears the retrieval card's shape: a technique card list over the resolution
 * API, with an advanced modal for the full reference. The options come from
 * `useQueryTransformationOptions`, so the panel only has to wire the section.
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
  const { transformers, generators, prompts, loading, loadError } =
    useQueryTransformationOptions();
  const [blockMessage, setBlockMessage] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const enabled = value != null;

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

  /**
   * Enables the stage with a transformer, or explains why it cannot be.
   * @param {object} transformer - The transformer component to enable.
   */
  const enableWith = (transformer) => {
    if (!transformer) {
      setBlockMessage(
        t("generative:rag.config.queryTransformation.noneAvailable"),
      );
      return;
    }
    const { ref, blockedBy } = prepareEnableRef({
      transformer,
      generators,
      defaultGeneratorName,
      prompts,
    });
    if (blockedBy) {
      setBlockMessage(
        t(`generative:rag.config.queryTransformation.${blockedBy}`),
      );
      return;
    }
    setBlockMessage(null);
    onChange(ref);
  };

  /**
   * Persists a ref edited in the advanced modal. Only a complete ref with a
   * downloaded model is accepted; turning the stage off is always allowed.
   * @param {object|null} ref - The edited stage ref, or null to disable.
   */
  const commitStage = (ref) => {
    if (ref && !canPersistQueryTransformationRef(ref, generators)) return;
    onChange(ref);
  };

  /**
   * Enables the stage with the technique a card stands for.
   * @param {object} preset - The selected technique card.
   */
  const handleSelect = (preset) => {
    const transformer = transformers.find(
      (component) => component.name === preset.component,
    );
    if (!transformer) {
      setBlockMessage(
        t("generative:rag.config.queryTransformation.unknownComponent", {
          component: preset.component,
        }),
      );
      return;
    }
    enableWith(transformer);
  };

  const unregistered =
    enabled &&
    section?.registered !== true &&
    !transformers.some((component) => component.name === value?.component);

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
        disabled={loading || Boolean(loadError)}
      />

      {unregistered && (
        <Alert severity="info" sx={{ py: 0.5 }}>
          {t("generative:rag.config.queryTransformation.unknownComponent", {
            component: value?.component,
          })}
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

      {enabled && (
        <QueryTransformationAdvancedModal
          open={showAdvanced}
          onClose={() => setShowAdvanced(false)}
          model={value}
          setModel={commitStage}
          technique={technique}
          generators={generators}
        />
      )}
    </Stack>
  );
}

QueryTransformationPicker.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func.isRequired,
  section: PropTypes.object,
};
