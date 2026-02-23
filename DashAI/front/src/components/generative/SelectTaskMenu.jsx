import { useTranslation } from "react-i18next";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";

export default function SelectTaskMenu({ tasks, goToNextStep }) {
  const { t } = useTranslation(["generative", "common"]);

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
