import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Centered card used by the session views (log in, register, change
 * password): app logo, title, the form and a footer below a divider.
 */
export default function AuthCard({ title, subtitle, footer, children }) {
  const theme = useTheme();

  return (
    <Box
      sx={{
        minHeight: "calc(100dvh - 53px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        px: 2,
        py: 6,
        boxSizing: "border-box",
      }}
    >
      <Box
        sx={{
          width: "100%",
          maxWidth: 400,
          p: { xs: 4, sm: 5 },
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 2,
          background: theme.palette.background.box,
          boxSizing: "border-box",
        }}
      >
        <Box sx={{ display: "flex", justifyContent: "center", mb: 4 }}>
          <Box
            component="img"
            src="/dashai-logo.svg"
            alt="dashAI"
            sx={{ height: 24, width: "auto" }}
          />
        </Box>

        <Typography
          variant="h5"
          sx={{ color: theme.palette.text.primary, textAlign: "center" }}
        >
          {title}
        </Typography>

        {subtitle && (
          <Typography
            variant="body2"
            sx={{
              color: theme.palette.text.disabled,
              textAlign: "center",
              mt: 1,
            }}
          >
            {subtitle}
          </Typography>
        )}

        <Box sx={{ mt: 4 }}>{children}</Box>

        {footer && (
          <>
            <Divider sx={{ my: 4 }} />
            <Typography
              variant="body2"
              component="div"
              sx={{ color: theme.palette.text.secondary, textAlign: "center" }}
            >
              {footer}
            </Typography>
          </>
        )}
      </Box>
    </Box>
  );
}

AuthCard.propTypes = {
  title: PropTypes.node.isRequired,
  subtitle: PropTypes.node,
  footer: PropTypes.node,
  children: PropTypes.node,
};
