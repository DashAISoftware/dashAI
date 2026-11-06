import { useState } from "react";
import { Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import { FormSchemaProvider } from "../../../../contexts/schema";
import ChunkingConfigurationStep from "./ChunkingConfigurationStep";
import RAGAdvancedDialog from "./RAGAdvancedDialog";
import { getModelFromSubform } from "../../../../utils/schema";

/**
 * Full-screen modal dialog for advanced chunking configuration.
 * Wraps ChunkingConfigurationStep in the shared RAG advanced dialog shell.
 *
 * @param {object} props
 * @param {boolean} props.open - Whether the dialog is open.
 * @param {function} props.onClose - Callback to close the dialog.
 * @param {object} [props.chunkingModel] - The current chunking model { component, params }.
 * @param {function} props.setChunkingModel - State setter for the chunking model.
 * @returns {JSX.Element} The advanced chunking modal.
 */
export default function ChunkingAdvancedModal({
  open,
  onClose,
  chunkingModel,
  setChunkingModel,
}) {
  const { t } = useTranslation(["generative"]);
  const [stepValid, setStepValid] = useState(false);
  const modelName = getModelFromSubform(chunkingModel);

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={onClose}
      title={t("generative:rag.advanced.chunkingTitle")}
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
      <FormSchemaProvider key={`chunking-advanced-${modelName}`}>
        <ChunkingConfigurationStep
          chunkingModel={chunkingModel}
          setChunkingModel={setChunkingModel}
          setNextEnabled={setStepValid}
        />
      </FormSchemaProvider>
    </RAGAdvancedDialog>
  );
}
