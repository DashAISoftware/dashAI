import React, { useState, useEffect } from "react";
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


const AVAILABLE_METHODS = [
    { name: "PtypeCat (Basic and Categorical Types)", value: "DashAIPtype"},
    { name: "Image File Detection", value: "Image"}
]

function InferenceMethodDialog({ 
    open, 
    onClose,
    onConfirm,
    defaultSelected = [],
}) {

    const [selectedMethods, setSelectedMethods] = useState(defaultSelected);

    useEffect(() => {
        setSelectedMethods(defaultSelected);
    }, [defaultSelected]);

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
            <DialogTitle>Inference Methods</DialogTitle>
            <DialogContent dividers>
                <Typography variant="body2" gutterBottom>
                    Select the inference methods you want to apply:
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
                    Cancel
                </Button>
                <Button variant="contained" onClick={handleConfirm} disabled={selectedMethods.length === 0}>
                    Confirm
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
    

