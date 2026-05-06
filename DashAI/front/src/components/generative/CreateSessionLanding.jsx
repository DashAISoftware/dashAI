import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import SelectOptionMenu from "../threeSectionLayout/SelectOptionMenu";

export default function CreateSessionLanding() {
  const navigate = useNavigate();
  const { t } = useTranslation(["generative", "common"]);

  return (
    <SelectOptionMenu
      goToNextStep={() => navigate("/app/generative/sessions/new")}
      title={t("generative:label.generativeModule")}
      subtitle={t("generative:label.createNewSessionDescription")}
      options={[
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
