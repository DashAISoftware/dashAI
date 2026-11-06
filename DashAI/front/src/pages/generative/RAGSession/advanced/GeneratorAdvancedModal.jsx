import { useState } from "react";
import { Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import { FormSchemaProvider } from "../../../../contexts/schema";
import GeneratorConfigurationStep from "./GeneratorConfigurationStep";
import RAGAdvancedDialog from "./RAGAdvancedDialog";

/**
 * Full-screen modal dialog for advanced generator (LLM) configuration.
 * Wraps GeneratorConfigurationStep in the shared RAG advanced dialog shell.
 *
 * @param {object} props
 * @param {boolean} props.open - Whether the dialog is open.
 * @param {function} props.onClose - Callback to close the dialog.
 * @param {object} [props.generatorModel] - The current generator model { component, params }.
 * @param {function} props.setGeneratorModel - State setter for the generator model.
 * @returns {JSX.Element} The advanced generator modal.
 */
export default function GeneratorAdvancedModal({
  open,
  onClose,
  generatorModel,
  setGeneratorModel,
}) {
  const { t } = useTranslation(["generative"]);
  const [stepValid, setStepValid] = useState(false);

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={onClose}
      title={t("generative:rag.advanced.generatorTitle")}
      actions={
        <>
          <Button onClick={onClose} variant="outlined">
            {t("generative:rag.advanced.close")}
          </Button>
          <Button
            onClick={onClose}
            variant="contained"
            color="primary"
            disabled={!stepValid}
          >
            {t("generative:rag.advanced.done")}
          </Button>
        </>
      }
    >
      <FormSchemaProvider
        key={`generator-advanced-${generatorModel?.component}`}
      >
        <GeneratorConfigurationStep
          generatorModel={generatorModel}
          setGeneratorModel={setGeneratorModel}
          setNextEnabled={setStepValid}
        />
      </FormSchemaProvider>
    </RAGAdvancedDialog>
  );
}
