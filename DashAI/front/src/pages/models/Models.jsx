import { TourProvider } from "../../components/tour/TourProvider";
import { TOUR_KEYS } from "../../constants/tours";
import ModelsContent from "./ModelsContent";
import { ModelsProvider } from "../../components/models/ModelsContext";

export default function Models() {
  return (
    <TourProvider tourKey={TOUR_KEYS.MODELS}>
      <ModelsProvider>
        <ModelsContent />
      </ModelsProvider>
    </TourProvider>
  );
}
