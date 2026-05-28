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
import { useTranslation } from "react-i18next";
import { FormSchemaProvider } from "../../../../contexts/schema";
import ChunkingConfigurationStep from "./ChunkingConfigurationStep";
import { getModelFromSubform } from "../../../../utils/schema";

export default function ChunkingAdvancedModal({
  open,
  onClose,
  chunkingModel,
  setChunkingModel,
}) {
  const { t } = useTranslation(["generative"]);
  const [stepValid, setStepValid] = useState(false);
  const modelName = getModelFromSubform(chunkingModel);

  const handleClose = () => {
    onClose();
  };

  const handleSave = () => {
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { minHeight: "500px" },
      }}
    >
      <DialogTitle
        sx={{
          bgcolor: "background.paper",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        {t("generative:simplifiedRag.advanced.chunkingTitle")}
        <IconButton
          onClick={handleClose}
          size="small"
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ bgcolor: "background.paper", minHeight: 400 }}>
        <FormSchemaProvider key={`chunking-advanced-${modelName}`}>
          <ChunkingConfigurationStep
            chunkingModel={chunkingModel}
            setChunkingModel={setChunkingModel}
            setNextEnabled={setStepValid}
          />
        </FormSchemaProvider>
      </DialogContent>

      <DialogActions sx={{ p: 2, bgcolor: "background.paper" }}>
        <Button onClick={handleClose} variant="outlined">
          {t("generative:simplifiedRag.advanced.close")}
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          color="primary"
          disabled={!stepValid}
        >
          {t("generative:simplifiedRag.advanced.done")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

