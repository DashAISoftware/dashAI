import { TourProvider } from "../../components/tour/TourProvider";
import { TOUR_KEYS } from "../../constants/tours";
import { GenerativeProvider } from "../../components/generative/GenerativeContext";
import GenerativeContent from "./GenerativeContent";

export default function Generative() {
  return (
    <TourProvider tourKey={TOUR_KEYS.GENERATIVE}>
      <GenerativeProvider>
        <GenerativeContent />
      </GenerativeProvider>
    </TourProvider>
  );
}
