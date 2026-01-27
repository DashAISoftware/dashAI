import { Avatar as MuiAvatar } from "@mui/material";
import { useTranslation } from "react-i18next";

export function ChatAvatar({ isUser, alt }) {
  const { t } = useTranslation(["common"]);
  return (
    <MuiAvatar
      src={isUser ? undefined : "/dai_circle.png"}
      alt={alt || (isUser ? t("common:user") : t("common:model"))}
      sx={{
        mr: isUser ? 0 : 1,
        ml: isUser ? 1 : 0,
        width: 32,
        height: 32,
      }}
    />
  );
}
