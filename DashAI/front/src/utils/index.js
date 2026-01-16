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
    case 0: // Not Started
      color = "#626262";
      break;
    case 1: // Delivered
      color = "#3e68ffff";
      break;
    case 3: // Finished
      color = "#43A047";
      break;
    case 2: // Started
      color = "#3e68ffff";
      break;
    case 4: // Error
      color = "#A70909";
      break;
    default:
      color = "#000000";
  }
  return color;
};

export const getColorByColumnType = (type) => {
  if (!type) return "#757575";

  const typeColors = {
    numerical: "#00BEBB",
    float: "#00BEBB",
    integer: "#3e68ff",
    int: "#3e68ff",
    number: "#00BEBB",

    categorical: "#9c27b0",
    category: "#9c27b0",

    text: "#f1ae61",
    string: "#f1ae61",

    boolean: "#43A047",
    bool: "#43A047",

    datetime: "#e91e63",
    date: "#e91e63",
    time: "#e91e63",
    timestamp: "#e91e63",

    image: "#6E86E8",

    default: "#757575",
  };

  const normalizedType = type.toLowerCase();
  return typeColors[normalizedType] || typeColors.default;
};
