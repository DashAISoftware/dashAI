import { useTranslation } from "react-i18next";
import {
    Box,
    Button,
    TextField,
    Typography,
    List,
    ListItemButton,
    ListItemText,
    IconButton,
    CircularProgress,
    Alert,
    Paper,
    Divider,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogContentText,
    DialogActions,
    Checkbox,
    FormControlLabel,
} from '@mui/material';

import AddIcon from '@mui/icons-material/Add';

import { useState, useEffect } from 'react';

const MODAL_DISMISSED_KEY = 'agenticModalDismissed';

export default function AgentModalWelcome() {
    const { t } = useTranslation();

    const [modalOpen, setModalOpen] = useState(false);
    const [dontShowAgain, setDontShowAgain] = useState(false);
    useEffect(() => {
        const dismissed = localStorage.getItem(MODAL_DISMISSED_KEY) === 'true';
        if (!dismissed) {
            setModalOpen(true);
        }
    }, []);

    const handleCloseModal = () => {
        if (dontShowAgain) {
            localStorage.setItem(MODAL_DISMISSED_KEY, 'true');
        }
        setModalOpen(false);
    };

    return (
        <Dialog
            open={modalOpen}
            onClose={handleCloseModal}
            maxWidth="md"
            fullWidth
            disableEscapeKeyDown
        >
            <DialogTitle variant="h4" sx={{ fontWeight: 'bold' }}>
                {t("agent:label.agentModality")}
            </DialogTitle>
            <DialogContent>
                <DialogContentText component="div">
                    <Typography variant="body1" paragraph>
                        {t("agent:message.agentDescription1")}
                    </Typography>
                    <Typography variant="body1" paragraph>
                        {t("agent:message.agentDescription2")}
                    </Typography>
                </DialogContentText>
                <Box sx={{ mt: 2 }}>
                    <FormControlLabel
                        control={
                            <Checkbox
                                checked={dontShowAgain}
                                onChange={(e) => setDontShowAgain(e.target.checked)}
                            />
                        }
                        label={t("agent:message.dontShowAgain")}
                    />
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={handleCloseModal} variant="contained" color="primary">
                    Cerrar
                </Button>
            </DialogActions>
        </Dialog>
    );
} 