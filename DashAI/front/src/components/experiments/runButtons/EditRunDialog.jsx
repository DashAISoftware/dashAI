import React, { useState } from "react";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { Edit } from "@mui/icons-material";

import RunInfoModal from "./RunInfoModal";
import { useTranslation } from "react-i18next";

export default function EditRunDialog({ experiment, run, setRun }) {
  const isRunning = run.status === 1 || run.status === 2;
  const [open, setOpen] = useState(false);
  const { t } = useTranslation("experiments");

  if (isRunning) {
    return null;
  }

  return (
    <>
      <GridActionsCellItem
        icon={<Edit />}
        label={t("button.editRun")}
        onClick={() => setOpen(true)}
      />
      {open && (
        <RunInfoModal
          experiment={experiment}
          run={run}
          open={open}
          onClose={() => setOpen(false)}
          setRun={setRun}
        />
      )}
    </>
  );
}
