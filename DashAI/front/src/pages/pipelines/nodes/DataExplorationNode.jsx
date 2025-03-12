import React, { useState, useEffect } from "react";
import { Box, Button, DialogContent, Typography, Checkbox, FormControlLabel, FormGroup } from "@mui/material";

const DataExplorationNode = ({ open, onClose, onSave, savedConfig }) => {
  // Opciones de exploración de datos
  const explorationOptions = [
    "Summary Statistics",
    "Missing Values Analysis",
    "Correlation Matrix",
    "Distribution Plots",
    "Outlier Detection",
  ];

  // Estado para las opciones seleccionadas
  const [selectedOptions, setSelectedOptions] = useState(savedConfig?.options || []);

  // Actualiza el estado cuando cambia savedConfig
  useEffect(() => {
    setSelectedOptions(savedConfig?.options || []);
  }, [savedConfig]);

  // Maneja el cambio en las opciones seleccionadas
  const handleOptionChange = (option) => {
    setSelectedOptions((prevOptions) =>
      prevOptions.includes(option)
        ? prevOptions.filter((opt) => opt !== option) // Desmarca la opción
        : [...prevOptions, option] // Marca la opción
    );
  };

  // Guarda la configuración
  const saveExplorationOptions = () => {
    onSave({ options: selectedOptions }); // Guarda las opciones seleccionadas
    onClose(); // Cierra el diálogo
  };

  return (
    <DialogContent>
      <Typography variant="body1" gutterBottom>
        Choose the data exploration options:
      </Typography>
      <Box mt={2}>
        <FormGroup>
          {explorationOptions.map((option) => (
            <FormControlLabel
              key={option}
              control={
                <Checkbox
                  checked={selectedOptions.includes(option)}
                  onChange={() => handleOptionChange(option)}
                />
              }
              label={option}
            />
          ))}
        </FormGroup>
      </Box>
      <Box mt={3}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          onClick={saveExplorationOptions}
          disabled={selectedOptions.length === 0}
        >
          Save Exploration Options
        </Button>
      </Box>
    </DialogContent>
  );
};

export default DataExplorationNode;
