import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Button,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

const AVAILABLE_METHODS = [
  { name: "PtypeCat (Basic and Categorical Types)", value: "DashAIPtype" },
  { name: "Image File Detection", value: "Image" },
];

const EMPTY_ARRAY = [];

function InferenceMethodDialog({
  open,
  onClose,
  onConfirm,
  defaultSelected = EMPTY_ARRAY,
}) {
  const [selectedMethods, setSelectedMethods] = useState(defaultSelected);
  const { t } = useTranslation(["custom", "common"]);

  const handleCheckboxChange = (method) => {
    setSelectedMethods((prev) => {
      if (prev.includes(method)) {
        return prev.filter((m) => m !== method);
      } else {
        return [...prev, method];
      }
    });
  };

  const handleConfirm = () => {
    onConfirm(selectedMethods);
    onClose();
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{t("custom:inferenceMethods")}</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" gutterBottom>
          {t("custom:selectInferenceMethods")}:
        </Typography>
        <FormGroup>
          {AVAILABLE_METHODS.map((method) => (
            <FormControlLabel
              key={method.value}
              control={
                <Checkbox
                  checked={selectedMethods.includes(method.value)}
                  onChange={() => handleCheckboxChange(method.value)}
                />
              }
              label={method.name}
            />
          ))}
        </FormGroup>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} color="secondary">
          {t("common:cancel")}
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={selectedMethods.length === 0}
        >
          {t("common:confirm")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
InferenceMethodDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onConfirm: PropTypes.func.isRequired,
  defaultSelected: PropTypes.array,
};

export default InferenceMethodDialog;
