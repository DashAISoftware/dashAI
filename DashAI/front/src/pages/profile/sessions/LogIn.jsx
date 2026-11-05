import React, { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "@mui/material/Link";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";

import AuthCard from "../mem-utils/AuthCard";
import PasswordField from "../mem-utils/PasswordField";
import { useSession } from "../mem-utils/SessionContext";
import { resetDemoData } from "../mem-utils/authService";

/* ==========================================================================
 * DEBUG — demo data (development only)
 *
 * When SHOW_DEMO_ACCOUNTS is true, the login view shows a button that resets
 * the mock accounts listed in the admin views (stored in this browser). Real
 * accounts live in the backend and are not affected.
 *
 * TODO: remove this block and its JSX section before closing the feature.
 * ========================================================================== */
const SHOW_DEMO_ACCOUNTS = true;

export default function LogIn() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useSession();

  // RequireAuth sends the path the user wanted to visit
  const needsLogin = location.state?.reason === "auth";
  const sessionExpired = location.state?.reason === "expired";
  const redirectTo = location.state?.from ?? "/app";

  // Email or nickname; the backend tells them apart by the "@"
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);

  const invalid = identifier === "" || password === "";

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      await login(identifier, password);
      navigate(redirectTo, { replace: true });
    } catch (loginError) {
      setError(loginError.message);
    }
  };

  const handleResetDemoData = async () => {
    await resetDemoData();
    // Reload so the session context reads the default accounts again
    window.location.reload();
  };

  return (
    <AuthCard
      title="Iniciar sesión"
      subtitle="Ingresa con tu cuenta de DashAI"
      footer={
        <>
          ¿No tienes una cuenta?{" "}
          <Link component={RouterLink} to="/app/register">
            Regístrate
          </Link>
        </>
      }
    >
      {needsLogin && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Para acceder a esta funcionalidad debes iniciar sesión.
        </Alert>
      )}

      {sessionExpired && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Tu sesión expiró o fue cerrada. Inicia sesión nuevamente.
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          label="Correo electrónico o nickname"
          autoComplete="username"
          value={identifier}
          onChange={(event) => {
            setIdentifier(event.target.value.trim());
            setError(null);
          }}
          size="small"
          fullWidth
          autoFocus={!identifier}
        />

        <PasswordField
          label="Contraseña"
          autoComplete="current-password"
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
            setError(null);
          }}
          autoFocus={Boolean(identifier)}
          sx={{ mt: 2 }}
        />

        <Button
          type="submit"
          variant="contained"
          fullWidth
          disableElevation
          disabled={invalid}
          sx={{ mt: 3, textTransform: "none" }}
        >
          Iniciar sesión
        </Button>
      </Box>

      {/* DEBUG — demo accounts, see SHOW_DEMO_ACCOUNTS at the top */}
      {SHOW_DEMO_ACCOUNTS && (
        <Box
          sx={{
            mt: 3,
            p: 2,
            border: "1px dashed",
            borderColor: "warning.main",
            borderRadius: 1,
          }}
        >
          <Typography
            variant="caption"
            sx={{ display: "block", mb: 1, color: "warning.main" }}
          >
            Modo desarrollo: cuentas simuladas del panel de administración
          </Typography>

          <Button
            size="small"
            color="warning"
            onClick={handleResetDemoData}
            sx={{ textTransform: "none" }}
          >
            Restablecer datos de prueba
          </Button>
        </Box>
      )}
    </AuthCard>
  );
}
