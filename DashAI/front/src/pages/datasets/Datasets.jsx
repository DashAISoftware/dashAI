import { DatasetsAndNotebooksProvider } from "../../components/custom/contexts/DatasetsAndNotebooksContext";
import DatasetsContent from "./DatasetsContent";

export default function DatasetsPage() {
  return (
    <DatasetsAndNotebooksProvider>
      <DatasetsContent />
    </DatasetsAndNotebooksProvider>
  );
}
