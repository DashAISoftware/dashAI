import { forwardRef } from "react";
import { Box, Typography } from "@mui/material";
import ItemMenu from "./ItemMenu";
import { useTheme } from "@mui/material/styles";

const ItemBoxAgent = forwardRef(function ItemBoxAgent(
  {
    isSelected,
    name,
    description,
    id,
    onClick,
    onDelete,
    onEdit,
    onInfo,
    deleteConfirmationContent,
    deleteConfirmationWarning,
  },
  ref,
) {

  const theme = useTheme();


  return (
    <Box
      ref={ref}
      sx={{
        width: "100%",
        height: "50px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderRadius: 1,
        cursor: isSelected ? "default" : "pointer",
        bgcolor: isSelected ? theme.palette.action.selected : "transparent",
        p: 0.5,
        "&:hover": {
          backgroundColor: isSelected
            ? theme.palette.action.selected
            : theme.palette.action.hover,
        },
      }}
      onClick={isSelected ? undefined : onClick}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-start",
          width: "100%",
          minWidth: 0,
          flex: 1,
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            width: "100%",
            minWidth: 0, // Permite que el contenido se encoja
          }}
        >

          <Typography
            variant="body2"
            color="text.primary"
            noWrap
            sx={{ fontSize: 14 }}
          >
            {name}
          </Typography>

          <Typography
            variant="caption"
            color="text.secondary"
            noWrap
            sx={{ fontSize: 10, pl: 1 }}
          >
            {description ? description : ""}
          </Typography>
        </Box>
      </Box>
      <ItemMenu
        itemId={id}
        onInfo={onInfo}
        onDelete={onDelete}
        onEdit={onEdit}
        deleteConfirmationContent={deleteConfirmationContent}
        deleteConfirmationWarning={deleteConfirmationWarning}
      />
    </Box>
  );
});

export default ItemBoxAgent;
