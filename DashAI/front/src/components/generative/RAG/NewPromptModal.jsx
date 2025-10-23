import React from "react";

import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Grid,
  IconButton,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

export default function NewPromptModal({ open, handleClose }) {
  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullWidth
      maxWidth="md"
      aria-labelledby="new-prompt-dialog-title"
      PaperProps={{ sx: { minHeight: 600, borderRadius: 2 } }}
    >
      <DialogTitle id="new-prompt-dialog-title">
        <Grid container alignItems="center" justifyContent="space-between">
          <Grid item>
            <Typography variant="h6" component="h2">
              Create New Prompt
            </Typography>
          </Grid>
          <Grid item>
            <IconButton edge="end" color="inherit" onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          </Grid>
        </Grid>
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body1" sx={{ mt: 2 }}>
          Hola mundo
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" onClick={handleClose}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}
