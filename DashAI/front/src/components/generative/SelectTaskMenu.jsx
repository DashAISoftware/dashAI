import { useTranslation } from "react-i18next";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";
import { useGenerative } from "./GenerativeContext";

export default function SelectTaskMenu() {
  const { t } = useTranslation(["generative", "common"]);
  const { tasks, setSelectedDisplayName, setSelectedTaskName, setStepIndex } =
    useGenerative();

  const goToNextStep = (taskName, displayName) => {
    setSelectedDisplayName(displayName);
    setSelectedTaskName(taskName);
    setStepIndex(1);
  };

  return (
    <SelectOptionMenu
      goToNextStep={(taskName) =>
        goToNextStep(
          taskName,
          tasks.find((t) => t.name === taskName).display_name,
        )
      }
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
