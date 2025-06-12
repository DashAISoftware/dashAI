import DataSelectorNode from "./nodes/DataSelectorNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import TrainNode from "./nodes/TrainNode";
import PredictionNode from "./nodes/PredictionNode";
import RetrieveModelNode from "./nodes/RetrieveModelNode"

const nodeComponentRegistry = {
  DataSelector: DataSelectorNode,
  DataExploration: DataExplorationNode,
  Train: TrainNode,
  Prediction: PredictionNode,
  RetrieveModel: RetrieveModelNode,
};

export default nodeComponentRegistry;
