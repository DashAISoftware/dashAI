export function getRunStatus(statusNumber, t) {
  switch (statusNumber) {
    case 0:
      return t("common:notStarted");
    case 1:
      return t("common:delivered");
    case 2:
      return t("common:started");
    case 3:
      return t("common:finished");
    case 4:
      return t("common:error");
    default:
      throw new Error(`Error ${statusNumber} is not a valid status`);
  }
}
