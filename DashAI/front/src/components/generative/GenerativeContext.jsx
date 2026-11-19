import { createContext, useContext, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSessions } from "../../hooks/generative/useSessions";
const GenerativeContext = createContext(null);

export const useGenerative = () => useContext(GenerativeContext);

/**
 * Provides the session list and task metadata for a generative module view.
 *
 * @param {object} props
 * @param {JSX.Element} props.children
 * @param {object} [props.sessionFilter] - Which sessions this subtree owns.
 *   Unset lists every session, so a workflow with its own entry point is
 *   still reachable from the module. A dedicated entry point passes its own
 *   workflow to scope its views to it.
 */
export function GenerativeProvider({ children, sessionFilter }) {
  const { t, i18n } = useTranslation(["generative", "common"]);

  const {
    selectedSessionId,
    setSelectedSessionId,
    tasks,
    setTasks,
    workflows,
    selectedTaskName,
    setSelectedTaskName,
    selectedWorkflowName,
    setSelectedWorkflowName,
    selectedDisplayName,
    setSelectedDisplayName,
    sessions,
    setSessions,
    paramsVersion,
    setParamsVersion,
    fetchSessions,
    fetchTasks,
    fetchWorkflows,
    deleteSessionById,
    deleteSessionsByIds,
    editSession,
  } = useSessions({ t, sessionFilter });
  const [stepIndex, setStepIndex] = useState(0);
  const [openSections, setOpenSections] = useState({});

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    fetchTasks();
    fetchWorkflows();
  }, [i18n.language]);

  const value = {
    selectedSessionId,
    setSelectedSessionId,
    tasks,
    setTasks,
    workflows,
    selectedTaskName,
    setSelectedTaskName,
    selectedWorkflowName,
    setSelectedWorkflowName,
    selectedDisplayName,
    setSelectedDisplayName,
    sessions,
    setSessions,
    paramsVersion,
    setParamsVersion,
    fetchSessions,
    fetchTasks,
    fetchWorkflows,
    stepIndex,
    setStepIndex,
    openSections,
    setOpenSections,
    deleteSessionById,
    deleteSessionsByIds,
    editSession,
  };

  return (
    <GenerativeContext.Provider value={value}>
      {children}
    </GenerativeContext.Provider>
  );
}
