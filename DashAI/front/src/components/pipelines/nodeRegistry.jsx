import DataSelectorNode from "./nodes/DataSelectorNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import TrainNode from "./nodes/TrainNode";
import RetrieveModelNode from "./nodes/RetrieveModelNode";

const nodeRegistry = {
  DataSelector: DataSelectorNode,
  DataExploration: DataExplorationNode,
  Train: TrainNode,
  RetrieveModel: RetrieveModelNode,
};

export default nodeRegistry;
