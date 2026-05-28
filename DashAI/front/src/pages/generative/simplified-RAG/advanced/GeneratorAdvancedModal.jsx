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
import GeneratorConfigurationStep from "./GeneratorConfigurationStep";

export default function GeneratorAdvancedModal({
  open,
  onClose,
  selectedGenerator,
  generatorModel,
  setGeneratorModel,
}) {
  const { t } = useTranslation(["generative"]);
  const [stepValid, setStepValid] = useState(false);

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
        {t("generative:simplifiedRag.advanced.generatorTitle")}
        <IconButton
          onClick={handleClose}
          size="small"
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers sx={{ bgcolor: "background.paper", minHeight: 400 }}>
        <FormSchemaProvider key={`generator-advanced-${generatorModel?.component}`}>
          <GeneratorConfigurationStep
            generatorModel={generatorModel}
            setGeneratorModel={setGeneratorModel}
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

