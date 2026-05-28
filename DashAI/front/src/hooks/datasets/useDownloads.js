import { useState, useCallback, useEffect } from "react";
import { useSnackbar } from "notistack";
import { useTranslation } from "react-i18next";
import { listDatafiles, deleteDatafile } from "../../api/hub";
import { subscribeJobs } from "../../utils/jobPoller";

export function useDownloads() {
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["hub"]);
  const [downloads, setDownloads] = useState([]);

  const fetchDownloads = useCallback(async () => {
    const data = await listDatafiles();
    setDownloads(data);
    return data;
  }, []);

  useEffect(() => {
    fetchDownloads().catch(() => {});
  }, [fetchDownloads]);

  useEffect(() => {
    const unsubscribe = subscribeJobs((jobs) => {
      if (Array.isArray(jobs) && jobs.some((j) => j.status === "finished")) {
        fetchDownloads().catch(() => {});
      }
    });
    return unsubscribe;
  }, [fetchDownloads]);

  const deleteDownloadById = useCallback(
    async (id) => {
      const name = downloads.find((d) => d.id === id)?.name ?? "";
      try {
        await deleteDatafile(id);
        setDownloads((prev) => prev.filter((d) => d.id !== id));
        enqueueSnackbar(t("hub:deleteSuccess", { name }), {
          variant: "success",
        });
        return true;
      } catch {
        enqueueSnackbar(t("hub:deleteError"), { variant: "error" });
        return false;
      }
    },
    [downloads, enqueueSnackbar, t],
  );

  const updateDownload = useCallback((updated) => {
    setDownloads((prev) =>
      prev.map((d) => (d.id === updated.id ? updated : d)),
    );
  }, []);

  const addDownload = useCallback((dl) => {
    setDownloads((prev) => [...prev, dl]);
  }, []);

  return {
    downloads,
    fetchDownloads,
    deleteDownloadById,
    updateDownload,
    addDownload,
  };
}
