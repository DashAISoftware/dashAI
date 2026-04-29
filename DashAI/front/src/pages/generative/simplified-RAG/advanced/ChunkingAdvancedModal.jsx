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
import ChunkingConfigurationStep from "../../RAG/NewSessionModal/ChunkingConfigurationStep";

export default function ChunkingAdvancedModal({
  open,
  onClose,
  chunkingModel,
  setChunkingModel,
}) {
  const [stepValid, setStepValid] = useState(false);

  const handleClose = () => {
    onClose();
  };

  const handleSave = () => {
    // For ChunkingConfigurationStep, it uses autoSave on FormSchema
    // which calls setChunkingModel on every change. 
    // Just closing is enough as state is already updated in parent via props.
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
        Advanced Chunking Configuration
        <IconButton
          onClick={handleClose}
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ minHeight: 400 }}>
        <FormSchemaProvider key={`chunking-advanced-${chunkingModel?.component}`}>
          <ChunkingConfigurationStep
            chunkingModel={chunkingModel}
            setChunkingModel={setChunkingModel}
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
