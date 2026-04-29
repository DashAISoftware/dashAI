import { useState } from "react";
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
import GeneratorConfigurationStep from "../../RAG/NewSessionModal/GeneratorConfigurationStep";

export default function GeneratorAdvancedModal({
  open,
  onClose,
  selectedGenerator,
  generatorModel,
  setGeneratorModel,
}) {
  const [stepValid, setStepValid] = useState(false);

  const handleClose = () => {
    onClose();
  };

  const handleSave = () => {
    // For GeneratorConfigurationStep, it uses autoSave on FormSchema
    // which calls setGeneratorModel on every change.
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
          zIndex: 1300,
        },
      }}
      BackdropProps={{
        sx: {
          zIndex: 1299,
        }
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        Advanced Generator Configuration
        <IconButton
          onClick={handleClose}
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ minHeight: 400 }}>
        <FormSchemaProvider key={`generator-advanced-${generatorModel?.component}`}>
          <GeneratorConfigurationStep
            generatorModel={generatorModel}
            setGeneratorModel={setGeneratorModel}
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
