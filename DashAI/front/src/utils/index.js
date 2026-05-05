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

export const getColorByStatus = (status, theme) => {
  if (!theme?.palette?.status) {
    // Fallback to hardcoded colors if theme is not available
    const fallbackColors = {
      0: "#626262", // Not Started
      1: "#3e68ffff", // Delivered
      2: "#3e68ffff", // Started
      3: "#43A047", // Finished
      4: "#A70909", // Error
    };
    return fallbackColors[status] || "#000000";
  }

  const statusMap = {
    0: theme.palette.status.notStarted,
    1: theme.palette.status.delivered,
    2: theme.palette.status.started,
    3: theme.palette.status.finished,
    4: theme.palette.status.error,
  };

  return statusMap[status] || "#000000";
};

export const getColorByColumnType = (type, theme) => {
  if (!type) {
    return theme?.palette?.dataType?.default || "#757575";
  }

  if (!theme?.palette?.dataType) {
    // Fallback to hardcoded colors if theme is not available
    const fallbackColors = {
      numerical: "#00BEBB",
      float: "#00BEBB",
      integer: "#5c6bc0",
      int: "#5c6bc0",
      number: "#00BEBB",
      categorical: "#9c27b0",
      category: "#9c27b0",
      text: "#d4a054",
      string: "#d4a054",
      boolean: "#8bc34a",
      bool: "#8bc34a",
      datetime: "#e91e63",
      date: "#e91e63",
      time: "#e91e63",
      timestamp: "#e91e63",
      image: "#6E86E8",
      default: "#757575",
    };
    const normalizedType = type.toLowerCase();
    return fallbackColors[normalizedType] || fallbackColors.default;
  }

  const typeColors = {
    numerical: theme.palette.dataType.numerical,
    float: theme.palette.dataType.numerical,
    number: theme.palette.dataType.numerical,

    integer: theme.palette.dataType.integer,
    int: theme.palette.dataType.integer,

    categorical: theme.palette.dataType.categorical,
    category: theme.palette.dataType.categorical,

    text: theme.palette.dataType.text,
    string: theme.palette.dataType.text,

    boolean: theme.palette.dataType.boolean,
    bool: theme.palette.dataType.boolean,

    datetime: theme.palette.dataType.datetime,
    date: theme.palette.dataType.datetime,
    time: theme.palette.dataType.datetime,
    timestamp: theme.palette.dataType.datetime,

    image: theme.palette.dataType.image,

    default: theme.palette.dataType.default,
  };

  const normalizedType = type.toLowerCase();
  return typeColors[normalizedType] || typeColors.default;
};
