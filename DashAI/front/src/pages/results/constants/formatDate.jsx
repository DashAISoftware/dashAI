import i18n from "i18next";

export const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  const options = {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    locale: i18n.language,
  };

  return date.toLocaleString(i18n.language, options);
};
