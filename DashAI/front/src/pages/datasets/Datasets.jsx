import { TourProvider } from "../../components/tour/TourProvider";
import { TOUR_KEYS } from "../../constants/tours";
import { DatasetsAndNotebooksProvider } from "../../components/custom/contexts/DatasetsAndNotebooksContext";
import DatasetsContent from "./DatasetsContent";

export default function DatasetsPage() {
  return (
    <TourProvider tourKey={TOUR_KEYS.DATASETS}>
      <DatasetsAndNotebooksProvider>
        <DatasetsContent />
      </DatasetsAndNotebooksProvider>
    </TourProvider>
  );
}
