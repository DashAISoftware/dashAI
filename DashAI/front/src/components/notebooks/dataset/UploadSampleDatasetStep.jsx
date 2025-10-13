import { useState, useEffect, useRef } from "react";
import { Box, CircularProgress, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { createDataset } from "../../../api/datasets";
import { enqueueDatasetJob } from "../../../api/job";
import { useTourContext } from "../../tour/TourProvider";

export default function UploadSampleDatasetStep({ 
  handleDatasetCreated, 
  backHome 
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [loadingStatus, setLoadingStatus] = useState("Preparing sample dataset...");
  const tourContext = useTourContext();
  const observerRef = useRef(null);
  
  const safelyAdvanceTour = () => {
    if (!tourContext?.run) return;
    
    const element = document.querySelector('.datasets-list');
    if (!element) {
      return;
    }
    
    try {
      tourContext.nextStep();
    } catch (error) {
      console.error('[UploadSampleDatasetStep] Error advancing tour:', error);
    }
  };
  
  const waitForElement = (selector, callback) => {
    const existingElement = document.querySelector(selector);
    if (existingElement) {
      callback();
      return;
    }
    if (observerRef.current) {
      observerRef.current.disconnect();
    }
    
    observerRef.current = new MutationObserver((mutations, obs) => {
      const element = document.querySelector(selector);
      if (element) {
        obs.disconnect();
        setTimeout(callback, 300);
      }
    });
    
    observerRef.current.observe(document.body, {
      childList: true,
      subtree: true
    });
  };

  useEffect(() => {
    const uploadSampleDataset = async () => {
      try {
        setLoadingStatus("Creating dataset entry...");
        const datasetName = "Personality Dataset";
        const newDataset = await createDataset(datasetName);
        
        enqueueSnackbar(`Dataset ${datasetName} created successfully`, {
          variant: "success",
        });

        setLoadingStatus("Loading personality_dataset.csv file...");
        const response = await fetch('/samples/personality_dataset.csv');
        if (!response.ok) {
          throw new Error(`Failed to fetch personality_dataset.csv: ${response.status}`);
        }
        
        const fileBlob = await response.blob();
        const file = new File([fileBlob], 'personality_dataset.csv', { type: 'text/csv' });
        
        setLoadingStatus("Processing dataset...");
        const params = {
          dataloader: "CSVDataLoader",
          name: datasetName,
          separator: ",",
        };
        
        try {
          const job = await enqueueDatasetJob(
            newDataset.id,
            file,
            "",
            params
          );
          
          handleDatasetCreated(newDataset, job);
          
          if (tourContext?.run) {
            const currentStepTarget = tourContext.steps[tourContext.stepIndex]?.target;
            if (currentStepTarget === 'body') {
              waitForElement('.datasets-list', () => {
                setTimeout(safelyAdvanceTour, 1000);
              });
            }
          }
          
        } catch (jobError) {
          console.error("Error enqueuing dataset job:", jobError);
          enqueueSnackbar("Error when trying to enqueue the dataset job.", {
            variant: "error",
          });
          backHome();
        }
      } catch (error) {
        console.error("Error uploading sample dataset:", error);
        backHome();
      }
    };
    
    uploadSampleDataset();
    
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }
    };
  }, [handleDatasetCreated, enqueueSnackbar, backHome, tourContext]);

  return (
    <Box 
      sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center', 
        p: 4,
        minHeight: 300
      }}
    >
      <CircularProgress size={60} thickness={4} sx={{ mb: 3 }} />
      <Typography variant="h6">
        {loadingStatus}
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }}>
        This won't take long. You'll be redirected automatically when complete.
      </Typography>
    </Box>
  );
}