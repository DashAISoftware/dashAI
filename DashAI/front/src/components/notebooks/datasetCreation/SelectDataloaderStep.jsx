import { useEffect } from "react";
import ComponentSelector from "../../custom/ComponentSelector";
import { Box, Button, CircularProgress, Stack } from "@mui/material";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

/**
 * This component renders a selector for available dataloaders
 * @param {function} goToNextStep - Function to navigate to the next step in the dataset creation flow.
 * @param {function} goToPrevStep - Function to navigate back to the previous step in the dataset creation flow.
 * @param {object} selectedDataloader - The currently selected dataloader
 * @param {function} setSelectedDataloader - Function to update the selected dataloader
 * @param {Array} dataloaders - List of available dataloaders (fetched by parent)
 * @param {boolean} loadingDataloaders - Whether dataloaders are still loading
 */
export default function SelectDataloaderStep({
  goToNextStep,
  goToPrevStep,
  selectedDataloader,
  setSelectedDataloader,
  dataloaders = [],
  loadingDataloaders = false,
}) {
  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets", "common"]);

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
    if (!loadingDataloaders && tourContext?.run) {
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
  }, [loadingDataloaders, tourContext]);

  return (
    <Stack sx={{ height: "100%", minHeight: 0, flex: 1 }} spacing={2}>
      <Box sx={{ flex: 1, minHeight: 0 }} data-tour="csv-dataloader-option">
        {loadingDataloaders ? (
          <Box
            sx={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CircularProgress />
          </Box>
        ) : (
          <ComponentSelector
            components={dataloaders.map((d) => ({
              ...d,
              category: d.metadata?.category,
            }))}
            categoryKey="category"
            selected={selectedDataloader || null}
            onSelect={(item) => {
              setSelectedDataloader(item);
              if (
                tourContext?.run &&
                item?.name?.toLowerCase().includes("csv")
              ) {
                tourContext.nextStep();
              }
            }}
            searchPlaceholder={t("datasets:searchDataloaders", {
              defaultValue: "Search data loaders...",
            })}
          />
        )}
      </Box>

      <Box
        sx={{
          pt: 2,
          borderTop: 1,
          borderColor: "divider",
          flexShrink: 0,
          display: "flex",
          justifyContent: "flex-end",
          gap: 1,
        }}
      >
        <Button variant="outlined" onClick={goToPrevStep}>
          {t("common:back")}
        </Button>
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={!selectedDataloader?.name}
          data-tour="dataloader-step-next-button"
        >
          {t("common:next")}
        </Button>
      </Box>
    </Stack>
  );
}
