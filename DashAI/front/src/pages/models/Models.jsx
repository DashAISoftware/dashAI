import { TourProvider } from "../../components/tour/TourProvider";
import { TOUR_KEYS } from "../../constants/tours";
import ModelsContent from "./ModelsContent";

export default function Models() {
  return (
    <TourProvider tourKey={TOUR_KEYS.MODELS}>
      <ModelsContent />
    </TourProvider>
  );
}
