import { useEffect, useState } from "react";
import { getGenerativeTask } from "../../api/generativeTask";
import { useTranslation } from "react-i18next";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";

export default function SelectTaskMenu({ goToNextStep }) {
  const [tasks, setTasks] = useState([]);
  const { t } = useTranslation(["generative", "common"]);

  useEffect(() => {
    getGenerativeTask().then(setTasks);
  }, []);

  return (
    <SelectOptionMenu
      goToNextStep={() => goToNextStep(task.name, task.display_name)}
      title={t("generative:label.generativeModule")}
      subtitle={t("generative:label.selectGenerativeTask")}
      options={tasks.map((task) => ({
        name: task.name,
        display_name: task.display_name,
        description: task.description,
      }))}
      searchBar={true}
    />
  );
}
