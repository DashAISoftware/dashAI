import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Stack,
  TextField,
  Button,
  Typography,
  Chip,
  Box,
  IconButton,
  InputAdornment,
} from "@mui/material";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";
import {
  getCredentials,
  authenticateCredential,
  deleteCredential,
} from "../../api/credentials";

function CredentialRow({ credential, onChanged }) {
  const { t } = useTranslation("credentials");
  const { enqueueSnackbar } = useSnackbar();
  const [key, setKey] = useState(credential.key ?? "");
  const [showKey, setShowKey] = useState(true);
  const [busy, setBusy] = useState(false);

  const handleVerify = async () => {
    setBusy(true);
    try {
      await authenticateCredential(credential.name, key);
      enqueueSnackbar(t("verifySuccess"), { variant: "success" });
      onChanged();
    } catch {
      enqueueSnackbar(t("verifyError"), { variant: "error" });
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async () => {
    setBusy(true);
    try {
      await deleteCredential(credential.name);
      setKey("");
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider", py: 2 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography variant="subtitle2">{credential.display_name}</Typography>
        <Chip
          size="small"
          color={credential.is_authenticated ? "success" : "default"}
          label={
            credential.is_authenticated
              ? t("authenticated")
              : t("notAuthenticated")
          }
        />
      </Stack>
      <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
        <TextField
          size="small"
          fullWidth
          type={showKey ? "text" : "password"}
          placeholder={t("keyPlaceholder")}
          value={key}
          onChange={(e) => setKey(e.target.value)}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  size="small"
                  aria-label="toggle key visibility"
                  onClick={() => setShowKey((prev) => !prev)}
                  edge="end"
                >
                  {showKey ? (
                    <VisibilityOffOutlinedIcon fontSize="small" />
                  ) : (
                    <VisibilityOutlinedIcon fontSize="small" />
                  )}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
        <Button
          onClick={handleVerify}
          disabled={busy || !key}
          variant="contained"
        >
          {t("verify")}
        </Button>
        {credential.is_authenticated && (
          <Button onClick={handleRemove} disabled={busy} color="error">
            {t("remove")}
          </Button>
        )}
      </Stack>
    </Box>
  );
}

CredentialRow.propTypes = {
  credential: PropTypes.object.isRequired,
  onChanged: PropTypes.func.isRequired,
};

export default function CredentialsDialog({ open, onClose }) {
  const { t } = useTranslation("credentials");
  const [credentials, setCredentials] = useState([]);

  const refresh = async () => {
    try {
      const data = await getCredentials();
      setCredentials(Array.isArray(data) ? data : []);
    } catch {
      // silently ignore fetch errors (e.g. in test environments)
    }
  };

  useEffect(() => {
    if (open) {
      refresh();
    }
  }, [open]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{t("title")}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {t("subtitle")}
        </Typography>
        {credentials.map((credential) => (
          <CredentialRow
            key={credential.name}
            credential={credential}
            onChanged={refresh}
          />
        ))}
      </DialogContent>
    </Dialog>
  );
}

CredentialsDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};
