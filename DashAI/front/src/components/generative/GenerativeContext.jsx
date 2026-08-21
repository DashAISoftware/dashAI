import { createContext, useContext, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSessions } from "../../hooks/generative/useSessions";
const GenerativeContext = createContext(null);

export const useGenerative = () => useContext(GenerativeContext);

export function GenerativeProvider({ children }) {
  const { t, i18n } = useTranslation(["generative", "common"]);

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
  } = useSessions({ t });
  const [stepIndex, setStepIndex] = useState(0);
  const [openSections, setOpenSections] = useState({});

  useEffect(() => {
    fetchSessions();
  }, []);

  useEffect(() => {
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
