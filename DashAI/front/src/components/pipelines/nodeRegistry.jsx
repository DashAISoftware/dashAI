import DataSelectorNode from "./nodes/DataSelectorNode";
import DataExplorationNode from "./nodes/DataExplorationNode";
import RetrieveModelNode from "./nodes/RetrieveModelNode";
import ConfigurableNode from "./nodes/ConfigurableNode";
import SplitDataNode from "./nodes/SplitDataNode";
import TaskAndModelNode from "./nodes/TaskAndModelNode";
import MetricsEvalNode from "./nodes/MetricsEvalNode";

const nodeRegistry = {
  DataSelector: DataSelectorNode,
  DataExploration: DataExplorationNode,
  RetrieveModel: RetrieveModelNode,
  Configurable: ConfigurableNode,
  SplitData: SplitDataNode,
  TaskAndModel: TaskAndModelNode,
  MetricsEval: MetricsEvalNode,
};

export default nodeRegistry;
