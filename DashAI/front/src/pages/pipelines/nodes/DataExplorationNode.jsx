import ConfigureExplorersModal from "./ExplorationModal";
import { ExplorationsProvider } from "../../../components/explorations/context";
import { useSnackbar } from "notistack";
import { useEffect, useRef } from "react";

const DataExplorationNode = ({ open, onClose, onSave, savedConfig, prevNodes }) => {
  const datasetNode = prevNodes?.find((node) => node?.file_path && node?.id);
  const datasetId = datasetNode?.id ?? null;
  const { enqueueSnackbar } = useSnackbar();

  const hasWarnedRef = useRef(false);
  useEffect(() => {
    if (open && !datasetId) {
      if (!hasWarnedRef.current) {
          enqueueSnackbar("Missing dataset", { variant: "warning" });
          hasWarnedRef.current = true;
      }
      return;
    }
  }, [open, datasetId]);
  
  const handleClose = () => {
    onClose();
  };

  const handleSave = (explorers) => {
    onSave(explorers);
    onClose();
  };
  
  return (
   <>
    {open && datasetId && (
      <ExplorationsProvider datasetId={datasetId}>
        <ConfigureExplorersModal open={open} onClose={handleClose} onSave={handleSave} savedConfig={savedConfig} />
      </ExplorationsProvider>
    )}
  </>
  );
};

export default DataExplorationNode;
