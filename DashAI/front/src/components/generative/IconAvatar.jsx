import { Box } from "@mui/material";
import { Avatar } from "@mui/material";

export default function IconAvatar({ src, size = 40 }) {
  return (
    <Avatar
      src={src}
      sx={{
        width: size,
        height: size,
      }}
    />
  );
}
