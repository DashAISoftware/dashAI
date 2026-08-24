import { useState } from "react";
import PropTypes from "prop-types";
import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import ScopeStepSessionConverter from "./ScopeStepSessionConverter";
import ParameterStepConverter from "../../notebooks/converterCreation/ParameterStepConverter";

/**
 * Session-flow counterpart to the notebook's FormConverterSection. Same
 * Scope -> Parameters stepper shape, but saving never calls the notebook's
 * persist-and-run API (`saveConverter`/`enqueueConverterJob`) — it only
 * appends `{ converter, params, columns }` to the wizard's local state via
 * `onAddConverter`, the same local-state-only contract the session flow
 * has always used for adding a converter.
 */
export default function FormSessionConverterSection({
  step,
  setStep,
  handleClose,
  tool,
  inputColumnNames,
  columnTypes,
  onAddConverter,
}) {
  const { t } = useTranslation(["models"]);
  const [columns, setColumns] = useState([]);

  const hasParams = Object.values(tool.schema.properties).length > 0;

  const handleSaveConverter = (params) => {
    onAddConverter({
      converter: tool.name,
      params: params || {},
      columns: columns.map((col) => col.columnName),
    });
    handleClose();
  };

  return (
    <Box
      sx={{
        overflow: "visible",
        display: "flex",
        flexDirection: "column",
        flex: 1,
        maxHeight: "100%",
        minHeight: 0,
      }}
    >
      {step === 0 && (
        <ScopeStepSessionConverter
          tool={tool}
          inputColumnNames={inputColumnNames}
          columnTypes={columnTypes}
          columns={columns}
          setColumns={setColumns}
          nextStep={
            hasParams
              ? () => setStep((s) => s + 1)
              : () => handleSaveConverter({})
          }
        />
      )}
      {step === 1 && (
        <ParameterStepConverter
          converter={tool.name}
          tool={tool}
          selectedColumns={columns}
          initialParams={{}}
          handleSaveConverter={handleSaveConverter}
          setStep={setStep}
          saveButtonText={t("models:button.addConverter")}
        />
      )}
    </Box>
  );
}

FormSessionConverterSection.propTypes = {
  step: PropTypes.number.isRequired,
  setStep: PropTypes.func.isRequired,
  handleClose: PropTypes.func.isRequired,
  tool: PropTypes.object.isRequired,
  inputColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnTypes: PropTypes.object,
  onAddConverter: PropTypes.func.isRequired,
};
