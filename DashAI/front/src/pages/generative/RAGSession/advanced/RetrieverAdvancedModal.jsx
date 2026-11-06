import { useState, useRef } from "react";
import { Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { FormSchemaProvider } from "../../../../contexts/schema";
import RetrieverConfigurationStep from "./RetrieverConfigurationStep";
import RAGAdvancedDialog from "./RAGAdvancedDialog";

/**
 * Full-screen modal dialog for advanced retriever configuration.
 * Wraps RetrieverConfigurationStep in the shared RAG advanced dialog shell.
 *
 * @param {object} props
 * @param {boolean} props.open - Whether the dialog is open.
 * @param {function} props.onClose - Callback to close the dialog.
 * @param {any} props.selectedParadigm - The currently selected retriever paradigm.
 * @param {Array} [props.allParadigms] - All available retriever paradigms.
 * @param {object} [props.retrieverModel] - The current retriever model.
 * @param {function} props.setRetrieverModel - State setter for the retriever model.
 * @param {string|null} [props.downloadMessage] - Names the models the retriever
 *   still needs downloaded; while set, the dialog cannot be confirmed.
 * @returns {JSX.Element} The advanced retriever modal.
 */
export default function RetrieverAdvancedModal({
  open,
  onClose,
  selectedParadigm,
  allParadigms,
  retrieverModel,
  setRetrieverModel,
  downloadMessage = null,
}) {
  const { t } = useTranslation(["generative"]);
  const [stepValid, setStepValid] = useState(false);
  const retrieverStepRef = useRef(null);

  /**
   * Triggers a save of the current form values and closes the modal.
   */
  const handleSave = () => {
    if (retrieverStepRef.current) {
      retrieverStepRef.current.saveFormValues();
    }
    onClose();
  };

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={onClose}
      title={t("generative:rag.advanced.retrieverTitle")}
      actions={
        <>
          {downloadMessage && (
            <Typography
              variant="caption"
              color="warning.main"
              sx={{ mr: "auto" }}
            >
              {downloadMessage}
            </Typography>
          )}
          <Button onClick={onClose} variant="outlined">
            {t("generative:rag.advanced.close")}
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            color="primary"
            disabled={!stepValid || Boolean(downloadMessage)}
          >
            {t("generative:rag.advanced.done")}
          </Button>
        </>
      }
    >
      <FormSchemaProvider
        key={`retriever-advanced-${retrieverModel?.component}`}
      >
        <RetrieverConfigurationStep
          ref={retrieverStepRef}
          allParadigms={allParadigms}
          retrieverModel={retrieverModel}
          setRetrieverModel={setRetrieverModel}
          setNextEnabled={setStepValid}
        />
      </FormSchemaProvider>
    </RAGAdvancedDialog>
  );
}
