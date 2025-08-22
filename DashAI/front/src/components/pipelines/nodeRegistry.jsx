import DataSelectorNode from "./nodes/DataSelectorNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import TrainNode from "./nodes/TrainNode";
import RetrieveModelNode from "./nodes/RetrieveModelNode";
import ConfigurableNode from "./nodes/ConfigurableNode";

const nodeRegistry = {
  DataSelector: DataSelectorNode,
  DataExploration: DataExplorationNode,
  Train: TrainNode,
  RetrieveModel: RetrieveModelNode,
  Configurable: ConfigurableNode,
};

export default nodeRegistry;
