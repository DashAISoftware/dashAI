import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { useTranslation } from "react-i18next";
import { useSessions } from "../../hooks/generative/useSessions";
const GenerativeContext = createContext(null);

export const useGenerative = () => useContext(GenerativeContext);

export function GenerativeProvider({ children }) {
  const { t } = useTranslation(["models", "datasets", "common"]);

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
  } = useSessions({ t });
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    fetchSessions();
    fetchTasks();
  }, []);

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
    deleteSessionById,
  };

  return (
    <GenerativeContext.Provider value={value}>
      {children}
    </GenerativeContext.Provider>
  );
}
