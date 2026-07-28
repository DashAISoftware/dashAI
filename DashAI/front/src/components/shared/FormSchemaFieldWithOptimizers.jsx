import PropTypes from "prop-types";
import React from "react";
import { FormControlLabel, Switch, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import OptimizeIntegerInput from "../configurableObject/Inputs/IntegerInputOptimize";
import OptimizeNumberInput from "../configurableObject/Inputs/NumberInputOptimize";
import FormSchemaFieldCard from "./FormSchemaFieldCard";

/**
 * Renders an optimizable numeric field (integer or number) inside a FormSchemaFieldCard.
 * The optimize toggle lives in the card header; the input body shows fixed value or
 * lower/upper bounds depending on the switch state.
 */
function FormSchemaFieldWithOptimizers({ objName, paramJsonSchema, field }) {
  const { type } = paramJsonSchema;
  const { t } = useTranslation(["common"]);

  const canOptimize = paramJsonSchema?.placeholder?.optimize !== undefined;

  // Derived directly from field.value rather than mirrored into local state —
  // a local copy synced via useEffect lags the real value by a render, which
  // briefly flashed the wrong mode (fixed-value defaults instead of the
  // saved range) whenever this field remounted with a fresh value.
  const switchState =
    field?.value?.optimize ?? paramJsonSchema?.placeholder?.optimize ?? false;

  const handleSwitchChange = () => {
    const toggled = !switchState;
    const placeholder = paramJsonSchema?.placeholder;
    const hasError = field?.error !== undefined;
    field.onChange({
      fixed_value: hasError
        ? (placeholder?.fixed_value ?? null)
        : (field?.value?.fixed_value ?? null),
      lower_bound: hasError
        ? (placeholder?.lower_bound ?? null)
        : (field?.value?.lower_bound ?? null),
      upper_bound: hasError
        ? (placeholder?.upper_bound ?? null)
        : (field?.value?.upper_bound ?? null),
      optimize: toggled,
    });
  };

  const optimizeToggle = canOptimize ? (
    <FormControlLabel
      label={
        <Typography variant="caption" color="text.secondary">
          {t("common:optimize")}
        </Typography>
      }
      labelPlacement="start"
      control={
        <Switch
          size="small"
          checked={switchState}
          onChange={handleSwitchChange}
        />
      }
      sx={{ mr: 0, gap: 1 }}
    />
  ) : null;

  const commonProps = {
    name: objName,
    value: field?.value,
    label: paramJsonSchema.title,
    onChange: field?.onChange,
    error: field?.error || undefined,
    description: paramJsonSchema?.description,
    placeholder: paramJsonSchema?.placeholder,
    externalSwitchState: switchState,
  };

  return (
    <FormSchemaFieldCard
      label={paramJsonSchema.title}
      paramKey={objName}
      description={paramJsonSchema?.description}
      headerRight={optimizeToggle}
    >
      {type === "integer" ? (
        <OptimizeIntegerInput {...commonProps} />
      ) : (
        <OptimizeNumberInput {...commonProps} />
      )}
    </FormSchemaFieldCard>
  );
}

FormSchemaFieldWithOptimizers.propTypes = {
  objName: PropTypes.string,
  paramJsonSchema: PropTypes.object,
  field: PropTypes.object,
};

export default FormSchemaFieldWithOptimizers;
