import { createContext, useContext, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSessions } from "../../hooks/generative/useSessions";
import { useSession } from "../../pages/profile/mem-utils/SessionContext";
const GenerativeContext = createContext(null);

export const useGenerative = () => useContext(GenerativeContext);

/**
 * Provides the session list and task metadata for a generative module view.
 *
 * @param {object} props
 * @param {JSX.Element} props.children
 * @param {object} [props.sessionFilter] - Which sessions this subtree owns.
 *   Unset lists every session, grouped by task — so a task with its own entry
 *   point is still reachable from the module. A dedicated entry point passes
 *   its own task to scope its views to it.
 */
export function GenerativeProvider({ children, sessionFilter }) {
  const { t, i18n } = useTranslation(["generative", "common"]);
  const { user } = useSession();

  const {
    selectedSessionId,
    setSelectedSessionId,
    tasks,
    setTasks,
    selectedTaskName,
    setSelectedTaskName,
    selectedDisplayName,
    setSelectedDisplayName,
    sessions,
    setSessions,
    paramsVersion,
    setParamsVersion,
    fetchSessions,
    fetchTasks,
    deleteSessionById,
    deleteSessionsByIds,
    editSession,
  } = useSessions({ t, sessionFilter });
  const [stepIndex, setStepIndex] = useState(0);
  const [openSections, setOpenSections] = useState({});

  useEffect(() => {
    // Without a session (as on the login page) the API answers 401; the
    // provider is mounted again once the user logs in (see ProjectScope)
    if (!user) return;
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    if (!user) return;
    fetchTasks();
  }, [i18n.language]);

  const value = {
    selectedSessionId,
    setSelectedSessionId,
    tasks,
    setTasks,
    selectedTaskName,
    setSelectedTaskName,
    selectedDisplayName,
    setSelectedDisplayName,
    sessions,
    setSessions,
    paramsVersion,
    setParamsVersion,
    fetchSessions,
    fetchTasks,
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
