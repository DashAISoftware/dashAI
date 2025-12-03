export const formatDate = (inputDate) => {
  if (inputDate == null) {
    return "";
  }
  const date = new Date(inputDate);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");

  return `${year}/${month}/${day} ${hours}:${minutes}`;
};

export const getColorByStatus = (status) => {
  let color;
  switch (status) {
    case "Not Started":
      color = "#626262";
      break;
    case "Delivered":
      color = "#3e68ffff";
      break;
    case "Finished":
      color = "#43A047";
      break;
    case "Started":
      color = "#3e68ffff";
      break;
    case "Error":
      color = "#A70909";
      break;
    default:
      color = "#000000";
  }
  return color;
};
