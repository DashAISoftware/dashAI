import { Box } from "@mui/material";
import { keyframes } from "@mui/system";

const dotFade = keyframes`
  0%, 80%, 100% { opacity: 0.2; }
  40% { opacity: 1; }
`;

export default function LoadingDots() {
  return (
    <Box component="span" sx={{ display: "inline-flex", gap: "2px" }}>
      {[0, 1, 2].map((i) => (
        <Box
          key={i}
          component="span"
          sx={{
            animation: `${dotFade} 1.2s ease-in-out ${i * 0.2}s infinite both`,
          }}
        >
          .
        </Box>
      ))}
    </Box>
  );
}
