import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import { getComponents as getComponentsRequest } from "../../../api/component";
import ItemSelectorWithInfo from "../../custom/ItemSelectorWithInfo";
import { Grid } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

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
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets", "common"]);
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
      enqueueSnackbar(t("datasets:error.fetchingDataloaders"), {
        variant: "error",
      });
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

  const handleNext = () => {
    if (tourContext?.run) {
      goToNextStep();
      const observer = new MutationObserver(() => {
        if (document.querySelector('[data-tour="upload-area"]')) {
          observer.disconnect();
          tourContext.nextStep();
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
    } else {
      goToNextStep();
    }
  };

  useEffect(() => {
    if (!loading && tourContext?.run) {
      setTimeout(() => {
        const cards = document.querySelectorAll('[role="button"]');
        cards.forEach((card) => {
          const cardText = card.textContent;
          if (cardText.includes("CSVDataLoader") || cardText.includes("CSV")) {
            card.setAttribute("data-tour", "csv-dataloader-option");
          }
        });
      }, 100);
    }
  }, [loading, tourContext]);

  // fetches the available dataloaders
  useEffect(() => {
    getCompatibleDataloaders();
  }, [t]);
  return (
    <Grid
      container
      direction="column"
      justifyContent="space-around"
      alignItems="stretch"
      spacing={2}
    >
      {/* List of dataloaders */}
      <Grid>
        {!loading && (
          <ItemSelectorWithInfo
            itemsList={dataloaders}
            selectedItem={selectedDataloader}
            setSelectedItem={(item) => {
              setSelectedDataloader(item);
              if (
                tourContext?.run &&
                item?.name?.toLowerCase().includes("csv")
              ) {
                tourContext.nextStep();
              }
            }}
            data-tour="csv-dataloader-option"
          />
        )}
      </Grid>
      <Grid sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
        <FormSchemaButtonGroup
          onCancel={goToPrevStep}
          onFormSubmit={handleNext}
          formik={{
            errors: selectedDataloader.display_name
              ? {}
              : { dataloader: t("common:required") },
          }}
          saveButtonText={t("common:next")}
          backButtonText={t("common:back")}
          dataTour="dataloader-step-next-button"
        />
      </Grid>
    </Grid>
  );
}
