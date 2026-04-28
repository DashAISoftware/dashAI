import { useState, useRef } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { FormSchemaProvider } from "../../../../contexts/schema";
import RetrieverConfigurationStep from "../../RAG/NewSessionModal/RetrieverConfigurationStep";

export default function RetrieverAdvancedModal({
  open,
  onClose,
  selectedParadigm,
  retrieverModel,
  setRetrieverModel,
}) {
  const [stepValid, setStepValid] = useState(false);
  const retrieverStepRef = useRef(null);

  const handleClose = () => {
    onClose();
  };

  const handleSave = () => {
    if (retrieverStepRef.current) {
      retrieverStepRef.current.saveFormValues();
    }
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          maxHeight: "90vh",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        Advanced Retriever Configuration
        <IconButton
          onClick={handleClose}
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ minHeight: 400 }}>
        <FormSchemaProvider key={`retriever-advanced-${retrieverModel?.component}`}>
          <RetrieverConfigurationStep
            ref={retrieverStepRef}
            retrieverModel={retrieverModel}
            setRetrieverModel={setRetrieverModel}
            setNextEnabled={setStepValid}
          />
        </FormSchemaProvider>
      </DialogContent>

      <DialogActions sx={{ p: 2 }}>
        <Button onClick={handleClose} color="inherit">
          Close
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          color="primary"
          disabled={!stepValid}
        >
          Save Changes
        </Button>
      </DialogActions>
    </Dialog>
  );
}
