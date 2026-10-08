import React, { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "@mui/material/Link";
import TextField from "@mui/material/TextField";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";

import AuthCard from "../mem-utils/AuthCard";
import PasswordField from "../mem-utils/PasswordField";
import { EMAIL_PATTERN } from "../mem-utils/validation";

export default function LogIn() {
  const navigate = useNavigate();
  const location = useLocation();

  // Register redirects here with the new account's email
  const justRegistered = Boolean(location.state?.registered);
  const [email, setEmail] = useState(location.state?.email ?? "");
  const [password, setPassword] = useState("");

  const invalid = !EMAIL_PATTERN.test(email) || password === "";

  const handleSubmit = (event) => {
    event.preventDefault();
    // No authentication yet: any valid input "logs in"
    navigate("/app");
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
      {justRegistered && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Cuenta creada. Ya puedes iniciar sesión.
        </Alert>
      )}

      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          label="Correo electrónico"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value.trim())}
          size="small"
          fullWidth
          autoFocus={!email}
        />

        <PasswordField
          label="Contraseña"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoFocus={Boolean(email)}
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
    </AuthCard>
  );
}
