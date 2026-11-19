import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import {
  INFERENCE_WORKFLOW_NAME,
  RAG_WORKFLOW_NAME,
} from "../../constants/generativeWorkflows";

export const WORKFLOW_ENTRY_POINTS = {
  [INFERENCE_WORKFLOW_NAME]: {
    newRoute: "/app/generative/sessions/new",
    sessionRoute: "/app/generative/sessions",
    Icon: AutoAwesomeIcon,
  },
  [RAG_WORKFLOW_NAME]: {
    newRoute: "/app/generative/rag",
    sessionRoute: "/app/generative/rag/sessions",
    Icon: MenuBookIcon,
  },
};

export function newSessionRouteFor(workflowName) {
  return WORKFLOW_ENTRY_POINTS[workflowName]?.newRoute ?? null;
}

export function sessionRouteFor(workflowName, sessionId) {
  const entry =
    WORKFLOW_ENTRY_POINTS[workflowName] ??
    WORKFLOW_ENTRY_POINTS[INFERENCE_WORKFLOW_NAME];
  return `${entry.sessionRoute}/${sessionId}`;
}
