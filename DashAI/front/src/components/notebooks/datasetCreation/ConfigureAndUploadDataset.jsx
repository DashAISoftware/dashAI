import { useState, useEffect } from "react";
import { Grid } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import Upload from "./Upload";
import { getComponents as getComponentsRequest } from "../../../api/component";
import { useSnackbar } from "notistack";
import DataloaderConfiguration from "./DataloaderConfiguration";
import {
  enqueueDatasetJob as enqueueDatasetRequest,
  startJobQueue,
} from "../../../api/job";

/**
 * This component combines in a single step the process of uploading a file and configuring the dataloader parameters.
 * @param {object} newDataset An object that stores all the important states for the dataset modal.
 * @param {function} setNewDataset function that modifies newDataset state
 * @param {function} setNextEnabled function to enable or disable the "Next" button in the modal.
 * @param {object} formSubmitRef useRef to trigger form submit from outside "ParameterForm" component
 */
export default function ConfigureAndUploadDataset({
  newDataset,
  setNewDataset,
  formSubmitRef,
  goToPrevStep,
  updateDatasets,
  backHome,
  handleDatasetCreated,
}) {
  const [schema, setSchema] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const [nextEnabled, setNextEnabled] = useState(false);
  const [requestError, setRequestError] = useState(false);

  const handleSubmitNewDataset = async () => {
    try {
      const name =
        newDataset.params.name === null
          ? newDataset.file.name
          : newDataset.params.name;
      newDataset.params["dataloader"] = newDataset.dataloader;

      await enqueueDatasetRequest(
        newDataset.file,
        name,
        newDataset.url,
        newDataset.params,
      );
      await startJobQueue();

      enqueueSnackbar("Dataset upload job started", { variant: "success" });

      // Create a temporary dataset object for immediate visualization
      const tempDataset = {
        id: `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`, // Unique temporary ID
        name: name,
        file_path: newDataset.file ? newDataset.file.name : newDataset.url,
        created: new Date().toISOString(),
        last_modified: new Date().toISOString(),
        status: "processing", // Indicate it's still being processed
      };

      // Call the callback if provided
      if (handleDatasetCreated) {
        handleDatasetCreated(tempDataset);
      } else {
        backHome();
      }
    } catch (error) {
      console.error(error);
      setRequestError(true);
      enqueueSnackbar("Error when trying to upload the dataset.", {
        variant: "error",
      });
      backHome();
    }
  };

  async function getSchema() {
    setLoading(true);
    try {
      const schema = await getComponentsRequest({
        model: newDataset.dataloader,
      });

      setSchema(schema);
    } catch (error) {
      setError(true);
      enqueueSnackbar(
        "Error while trying to obtain json object for the selected dataloader",
      );
      if (error.response) {
        console.error("Response error:", error.message);
      } else if (error.request) {
        console.error("Request error", error.request);
      } else {
        console.error("Unknown Error", error.message);
      }
    } finally {
      setLoading(false);
    }
  }

  const handleFileUpload = (file, url) => {
    setNewDataset({ ...newDataset, file, url });
  };

  // fetch json schema with the dataloader parameters
  useEffect(() => {
    getSchema();
  }, []);

  useEffect(() => {
    if (newDataset.file !== null && !error) {
      setNextEnabled(true);
    } else {
      setNextEnabled(false);
    }
  }, [error, newDataset.file]);

  return (
    <Grid sx={{ p: 4 }}>
      <Grid
        container
        direction="row"
        justifyContent="space-around"
        alignItems="stretch"
        spacing={3}
      >
        {/* Upload file */}
        <Grid item xs={12} md={5}>
          <Upload onFileUpload={handleFileUpload} />
        </Grid>

        {/* Configure dataloader parameters */}
        <Grid item xs={12} md={7}>
          {!loading && Object.keys(schema).length > 0 && (
            <DataloaderConfiguration
              dataloader={newDataset.dataloader}
              paramsSchema={schema}
              formSubmitRef={formSubmitRef}
              onSubmit={(values) => {
                setNewDataset((prev) => {
                  return { ...prev, params: values };
                });
              }}
              newDataset={newDataset}
              setError={setError}
              error={error}
            />
          )}
        </Grid>
      </Grid>
      <Grid item sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
        <FormSchemaButtonGroup
          onCancel={goToPrevStep}
          onFormSubmit={handleSubmitNewDataset}
          formik={{
            errors: nextEnabled ? {} : { dataset: "Required fields missing" },
          }}
          saveButtonText="Upload"
          backButtonText="Back"
        />
      </Grid>
    </Grid>
  );
}
