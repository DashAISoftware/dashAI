import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";
import { useTourContext } from "../tour/TourProvider";
import { useGenerative } from "./GenerativeContext";
import {
  WORKFLOW_ENTRY_POINTS,
  newSessionRouteFor,
} from "./workflowEntryPoints";
import { INFERENCE_WORKFLOW_NAME } from "../../constants/generativeWorkflows";

/**
 * Landing of the Generative module.
 *
 * Offers one entry per workflow the backend reports, each with its name and
 * description, so model inference and RAG sit at the same level.
 *
 * @returns {JSX.Element} The module landing menu.
 */
export default function CreateSessionLanding() {
  const navigate = useNavigate();
  const { t } = useTranslation(["generative", "common"]);
  const tourContext = useTourContext();
  const { workflows } = useGenerative();

  const options = useMemo(
    () =>
      (workflows ?? [])
        .filter((workflow) => WORKFLOW_ENTRY_POINTS[workflow.name])
        .map((workflow) => ({
          name: workflow.name,
          display_name: workflow.display_name || workflow.name,
          description: workflow.description || "",
          Icon: WORKFLOW_ENTRY_POINTS[workflow.name].Icon,
        })),
    [workflows],
  );

  /**
   * Navigate to the chosen workflow's creation page.
   * @param {string} name - The workflow name.
   */
  const handleOption = (name) => {
    if (tourContext?.run) {
      tourContext.nextStep();
    }
    navigate(newSessionRouteFor(name));
  };

  return (
    <SelectOptionMenu
      goToNextStep={handleOption}
      title={t("generative:label.generativeModule")}
      subtitle={t("generative:label.createNewSessionDescription")}
      options={options}
      searchBar={false}
      dataTour="create-session-landing"
      dataTourTarget={INFERENCE_WORKFLOW_NAME}
    />
  );
}
