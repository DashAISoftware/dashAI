import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import TextSnippetIcon from "@mui/icons-material/TextSnippet";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";
import { useTourContext } from "../tour/TourProvider";

export default function CreateSessionLanding() {
  const navigate = useNavigate();
  const { t } = useTranslation(["generative", "common"]);
  const tourContext = useTourContext();

  const handleOption = (name) => {
    if (name === "RAGTask") {
      navigate("/app/generative/rag");
      return;
    }
    if (tourContext?.run) {
      tourContext.nextStep();
    }
    navigate("/app/generative/sessions/new");
  };

  return (
    <SelectOptionMenu
      goToNextStep={handleOption}
      title={t("generative:label.generativeModule")}
      subtitle={t("generative:label.createNewSessionDescription")}
      options={[
        {
          name: "RAGTask",
          display_name: t("generative:label.ragTask"),
          description: t("generative:label.ragTaskDescription"),
          Icon: TextSnippetIcon,
        },
        {
          name: "new_session",
          display_name: t("generative:label.createNewSession"),
          description: t("generative:label.createNewSessionDescription"),
          Icon: AutoAwesomeIcon,
        },
      ]}
      searchBar={false}
      dataTour="create-session-landing"
    ></SelectOptionMenu>
  );
}
