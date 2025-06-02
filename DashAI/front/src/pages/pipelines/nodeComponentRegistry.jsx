import DataSelectorNode from "./nodes/DataSelectorNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import TrainNode from "./nodes/TrainNode";
import PredictionNode from "./nodes/PredictionNode";

const nodeComponentRegistry = {
  DataSelector: DataSelectorNode,
  DataExploration: DataExplorationNode,
  Train: TrainNode,
  Prediction: PredictionNode,
};

export default nodeComponentRegistry;
