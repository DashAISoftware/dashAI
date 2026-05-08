import ModelsContent from "./ModelsContent";
import { ModelsProvider } from "../../components/models/ModelsContext";

export default function Models() {
  return (
    <ModelsProvider>
      <ModelsContent />
    </ModelsProvider>
  );
}
