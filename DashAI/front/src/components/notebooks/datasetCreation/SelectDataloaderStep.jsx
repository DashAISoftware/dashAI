import { useEffect, useState } from "react";
import { useSnackbar } from "notistack";
import { getComponents as getComponentsRequest } from "../../../api/component";
import ItemSelectorWithInfo from "../../custom/ItemSelectorWithInfo";
import { Grid } from "@mui/material";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

/**
 * This component renders a selector for available dataloaders
 * @param {object} selectedDataloader - The currently selected dataloader
 * @param {function} setSelectedDataloader - Function to update the selected dataloader
 */
export default function SelectDataloaderStep({
  selectedDataloader,
  setSelectedDataloader,
}) {
  const tourContext = useTourContext();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["datasets"]);
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
    </Grid>
  );
}
