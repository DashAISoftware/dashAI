import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import { getComponents as getComponentsRequest } from "../../../api/component";
import ItemSelectorWithInfo from "../../custom/ItemSelectorWithInfo";
import { Grid } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";

/**
 * This component renders a selector for available dataloaders
 * @param {function} goToNextStep - Function to navigate to the next step in the dataset creation flow.
 * @param {function} goToPrevStep - Function to navigate back to the previous step in the dataset creation flow.
 * @param {object} selectedDataloader - The currently selected dataloader
 * @param {function} setSelectedDataloader - Function to update the selected dataloader
 */
export default function SelectDataloaderStep({
  goToNextStep,
  goToPrevStep,
  selectedDataloader,
  setSelectedDataloader,
}) {
  const { enqueueSnackbar } = useSnackbar();

  const [dataloaders, setDataloaders] = useState([]);
  const [loading, setLoading] = useState(true);

  async function getCompatibleDataloaders() {
    setLoading(true);
    try {
      const dataloaders = await getComponentsRequest({
        selectTypes: ["DataLoader"],
      });
      setDataloaders(dataloaders);
    } catch (error) {
      enqueueSnackbar("Error while trying to obtain compatible dataloaders");
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

  // fetches the available dataloaders
  useEffect(() => {
    getCompatibleDataloaders();
  }, []);
  return (
    <Grid
      container
      direction="column"
      justifyContent="space-around"
      alignItems="stretch"
      spacing={2}
    >
      {/* List of dataloaders */}
      <Grid item>
        {!loading && (
          <ItemSelectorWithInfo
            itemsList={dataloaders}
            selectedItem={selectedDataloader}
            setSelectedItem={setSelectedDataloader}
          />
        )}
      </Grid>
      <Grid item sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
        <FormSchemaButtonGroup
          onCancel={goToPrevStep}
          onFormSubmit={goToNextStep}
          formik={{
            errors: selectedDataloader.name ? {} : { dataloader: "Required" },
          }}
          saveButtonText="Next"
          backButtonText="Back"
        />
      </Grid>
    </Grid>
  );
}
