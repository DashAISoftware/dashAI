import { TourProvider } from "../../components/tour/TourProvider";
import { TOUR_KEYS } from "../../constants/tours";
import DatasetsContent from "./DatasetsContent"; 

export default function DatasetsPage() {
  return (
    <TourProvider tourKey={TOUR_KEYS.DATASETS}>
      <DatasetsContent />
    </TourProvider>
  );
}