import { t } from "i18next";

export const getDisplaySetName = (displaySet) => {
  switch (displaySet) {
    case "test_metrics":
      return t("models:label.testSet");
    case "train_metrics":
      return t("models:label.trainSet");
    case "validation_metrics":
      return t("models:label.validationSet");
    default:
      throw new Error(`Error, set name ${displaySet} is not recognized`);
  }
};
