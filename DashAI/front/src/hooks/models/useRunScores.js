import { useEffect, useMemo, useState } from "react";
import api from "../../api/api";

/**
 * Fetches the same weighted 0-100 score shown in ModelComparisonTable's
 * "Score" column, keyed by run id, so other views (e.g. the compact model
 * cards) can display an identical number. Also owns the scoring-profile
 * selection so it can be shared/controlled across components.
 */
export function useRunScores({ session, runs, metricSplit }) {
  const [profiles, setProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [scores, setScores] = useState({});
  const [loadingScores, setLoadingScores] = useState(false);

  useEffect(() => {
    const fetchProfiles = async () => {
      try {
        const params = {};
        if (session?.task_name) {
          params.task_name = session.task_name;
        }
        const response = await api.get("/v1/scoring/profiles", { params });
        const profilesList = response.data;
        setProfiles(profilesList);

        setSelectedProfile((prevProfile) => {
          if (profilesList.length === 0) return null;
          const profileExists = profilesList.some((p) => p.id === prevProfile);
          return profileExists ? prevProfile : profilesList[0].id;
        });
      } catch (error) {
        console.error("Error fetching scoring profiles:", error);
      }
    };
    fetchProfiles();
  }, [session?.task_name]);

  // Stable string that changes only when a run's status changes, so scores
  // re-fetch after training completes without firing on every re-render.
  const runStatusSignature = useMemo(
    () => runs.map((r) => `${r.id}:${r.status}`).join(","),
    [runs],
  );

  useEffect(() => {
    if (!runs.length || !selectedProfile || !session?.id) {
      setScores({});
      return;
    }

    let cancelled = false;
    const fetchScores = async () => {
      setLoadingScores(true);
      try {
        const response = await api.get("/v1/run/", {
          params: {
            model_session_id: session.id,
            include_scores: true,
            profile_id: selectedProfile,
            metric_split: metricSplit,
          },
        });
        if (cancelled) return;
        const scoresMap = {};
        response.data.forEach((run) => {
          if (run.score) scoresMap[run.id] = run.score;
        });
        setScores(scoresMap);
      } catch (error) {
        console.error("Error fetching scores:", error);
      } finally {
        if (!cancelled) setLoadingScores(false);
      }
    };
    fetchScores();

    return () => {
      cancelled = true;
    };
  }, [selectedProfile, metricSplit, session?.id, runStatusSignature]);

  return {
    profiles,
    selectedProfile,
    setSelectedProfile,
    scores,
    loadingScores,
  };
}
