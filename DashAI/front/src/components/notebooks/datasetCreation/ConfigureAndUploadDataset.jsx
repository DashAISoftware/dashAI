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

import { createDataset } from "../../../api/datasets";

/**
 * This component combines in a single step the process of uploading a file and configuring the dataloader parameters.
 * It creates the dataset entry in the database and then enqueues a job to process the uploaded file.
 *
 * @param {object} newDataset - An object that stores all the important states for the dataset modal (file, url, params, dataloader).
 * @param {function} setNewDataset - Function that modifies newDataset state.
 * @param {object} formSubmitRef - useRef to trigger form submit from outside "ParameterForm" component.
 * @param {function} goToPrevStep - Function to navigate back to the previous step in the dataset creation flow.
 * @param {function} backHome - Function to navigate back to the home/initial state, typically called on error.
 * @param {function} handleDatasetCreated - Callback function called when dataset is successfully created, receives the created dataset data.
 */

export default function ConfigureAndUploadDataset({
  newDataset,
  setNewDataset,
  formSubmitRef,
  goToPrevStep,
  backHome,
  handleDatasetCreated,
}) {
  const [schema, setSchema] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const [nextEnabled, setNextEnabled] = useState(false);

  const handleSubmitNewDataset = async () => {
    const name =
      newDataset.params.name === null
        ? newDataset.file.name
        : newDataset.params.name;

    newDataset.params["name"] = name;
    newDataset.params["dataloader"] = newDataset.dataloader;

    createDataset(name)
      .then((data) => {
        enqueueSnackbar(`Dataset ${data.name} created successfully`, {
          variant: "success",
        });
        enqueueDatasetRequest(
          data.id,
          newDataset.file,
          newDataset.url,
          newDataset.params,
        )
          .then(() => {
            startJobQueue();
          })
          .catch(() => {
            enqueueSnackbar("Error when trying to enqueue the dataset job.", {
              variant: "error",
            });
          });

        handleDatasetCreated(data);
      })
      .catch(() => {
        enqueueSnackbar("Error when trying to create the dataset.", {
          variant: "error",
        });
        backHome();
      });
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
