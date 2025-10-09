import { useState, useEffect } from "react";
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
          
          if (tourContext && tourContext.run) {
            waitForElement('.datasets-list', () => {
              setTimeout(() => {
                tourContext.nextStep();
              }, 500);
            });
          }
        } catch (jobError) {
          console.error("Error enqueuing dataset job:", jobError);
          enqueueSnackbar("Error when trying to enqueue the dataset job.", {
            variant: "error",
          });
          backHome();
        }
      } catch (error) {
        backHome();
      }
    };
    
    uploadSampleDataset();
  }, [handleDatasetCreated, enqueueSnackbar, backHome, tourContext]);

  const waitForElement = (selector, callback, timeout = 10000) => {
    const startTime = Date.now();
    
    const existingElement = document.querySelector(selector);
    if (existingElement) {
      callback();
      return;
    }
    const observer = new MutationObserver((mutations, obs) => {
      const element = document.querySelector(selector);
      if (element) {
        obs.disconnect();
        callback();
      } else if (Date.now() - startTime > timeout) {
        obs.disconnect();
        console.warn(`Timeout waiting for element: ${selector}`);
      }
    });
    
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  };

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