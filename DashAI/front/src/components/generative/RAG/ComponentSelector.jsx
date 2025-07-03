import React, { useEffect, useState } from 'react';
import { Box, Typography, TextField, CircularProgress } from '@mui/material';
import Autocomplete from '@mui/material/Autocomplete';


export default function ComponentSelector({
  componentType,
  fetchComponents,
  initialValues,
  onConfigurationChange,
  setNextEnabled
}) {
  const [components, setComponents] = useState([]);
  const [selectedComponent, setSelectedComponent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formValues, setFormValues] = useState({});

  // Cargar componentes disponibles
  useEffect(() => {
    const loadComponents = async () => {
      try {
        const data = await fetchComponents();
        setComponents(data);
        
        // Seleccionar componente inicial si existe
        if (initialValues?.model_name) {
          const component = data.find(c => c.name === initialValues.model_name);
          if (component) {
            setSelectedComponent(component);
            setFormValues(initialValues.parameters || {});
          }
        }
      } catch (error) {
        console.error(`Error loading ${componentType} components:`, error);
      } finally {
        setLoading(false);
      }
    };

    loadComponents();
  }, []);

  // Actualizar cuando cambia la selección
  useEffect(() => {
    if (selectedComponent) {
      // Resetear valores al cambiar de componente
      setFormValues(initialValues?.parameters || {});
      
      // Notificar cambio
      onConfigurationChange({
        model_name: selectedComponent.name,
        parameters: initialValues?.parameters || {}
      });
    }
  }, [selectedComponent]);

  // Validar y habilitar siguiente paso
  useEffect(() => {
    setNextEnabled(!!selectedComponent);
  }, [selectedComponent]);

  const handleParameterChange = (name, value) => {
    const newValues = {...formValues, [name]: value};
    setFormValues(newValues);
    
    // Notificar cambios en tiempo real
    if (selectedComponent) {
      onConfigurationChange({
        model_name: selectedComponent.name,
        parameters: newValues
      });
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Select {componentType}
      </Typography>
      
      {loading ? (
        <CircularProgress />
      ) : (
        <>
          <Autocomplete
            options={components.map(c => c.name)}
            value={selectedComponent?.name || ""}
            onChange={(_, newValue) => {
              const component = components.find(c => c.name === newValue);
              setSelectedComponent(component);
            }}
            renderInput={(params) => (
              <TextField 
                {...params} 
                label={`${componentType} Model`} 
                variant="outlined" 
              />
            )}
            fullWidth
            sx={{ mb: 3 }}
          />
          
          {selectedComponent && (
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Configuration Parameters
              </Typography>
              
              {selectedComponent.schema && Object.entries(selectedComponent.schema.properties).map(([key, spec]) => (
                <TextField
                  key={key}
                  label={spec.title || key}
                  value={formValues[key] || ""}
                  onChange={(e) => handleParameterChange(key, e.target.value)}
                  fullWidth
                  margin="normal"
                  type={spec.type === 'integer' ? 'number' : 'text'}
                  helperText={spec.description}
                />
              ))}
            </Box>
          )}
        </>
      )}
    </Box>
  );
}