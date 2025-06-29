
import React from "react";
import PropTypes from "prop-types";

import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
} from "@mui/icons-material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { Button, Grid, Paper, Typography, LinearProgress } from "@mui/material";
import { useSnackbar } from "notistack";

import { getRAGSessions, deleteRAGSession } from "../../../api/rag"; // Adjust the import path as necessary

function RAGSessionsTable({
    handleOpenNewSessionModal,
    onSessionSelect,
    updateTableFlag,
    setUpdateTableFlag,
}) {
    console.log("RAGSessionsTable rendered");
    const [loading, setLoading] = React.useState(true);
    const [sessions, setSessions] = React.useState([]);
    const { enqueueSnackbar } = useSnackbar();
    
    const getSessions = async () => {
        setLoading(true);
        try {
            const data = await getRAGSessions();
            setSessions(data);
        } catch (error) {
            console.error("[getSessions] error:", error);
            enqueueSnackbar("Error fetching RAG sessions", { variant: "error" });
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteSession = async (sessionId) => {
        try {
            await deleteRAGSession(sessionId);
            enqueueSnackbar("RAG session successfully deleted.", { 
                variant: "success"
            });
            getSessions(); // Refresh sessions after deletion
        } catch (error) {
            console.error("[deleteSession] error:", error);
            enqueueSnackbar("Error deleting RAG session", { variant: "error" });
        }
    };

    const handleOpenSession = (session) => {
        if (onSessionSelect) {
            onSessionSelect(session);
        }
    };

    const handleViewDocuments = (session) => {
        console.log("View documents for session:", session.id);
    };

    // FIXED: Moved useEffect to top level
    React.useEffect(() => {
        console.log("Initial load effect");
        getSessions();
    }, []);

    // FIXED: Added updateTableFlag effect
    React.useEffect(() => {
        if (updateTableFlag) {
            console.log("Update table flag triggered");
            getSessions();
            setUpdateTableFlag(false);
        }
    }, [updateTableFlag, setUpdateTableFlag]);

    // FIXED: Correct DataGrid column structure
    const columns = [
        { 
            field: "name", 
            headerName: "Session Name", 
            flex: 1 
        },
        { 
            field: "created_at", 
            headerName: "Created At", 
            flex: 1,
            valueFormatter: (params) => new Date(params.value).toLocaleString()
        },
        { 
            field: "documents", 
            headerName: "Documents", 
            flex: 0.7,
            valueGetter: (params) => params.row.documents?.length || 0
        },
        {
            field: "actions",
            headerName: "Actions",
            flex: 1.5,
            renderCell: (params) => (
                <div>
                    <Button 
                        size="small" 
                        onClick={() => handleOpenSession(params.row)}
                        sx={{ mr: 1 }}
                    >
                        Open
                    </Button>
                    <Button 
                        size="small" 
                        onClick={() => handleViewDocuments(params.row)}
                        sx={{ mr: 1 }}
                    >
                        View Docs
                    </Button>
                    <Button 
                        size="small" 
                        color="error"
                        onClick={() => handleDeleteSession(params.id)}
                    >
                        Delete
                    </Button>
                </div>
            )
        }
    ];

    return (
        <Paper sx={{ py: 4, px: 6 }}>
            <Grid container justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
                <Typography variant="h5" component="h2">
                    RAG Sessions
                </Typography>
                <Button
                    variant="contained"
                    color="primary"
                    onClick={handleOpenNewSessionModal}
                    startIcon={<AddIcon />}
                >
                    New RAG Session
                </Button>
            </Grid>

            <DataGrid
                rows={sessions}
                columns={columns}
                initialState={{
                    pagination: { paginationModel: { pageSize: 5 } },
                }}
                pageSizeOptions={[5, 10]}
                disableRowSelectionOnClick
                autoHeight
                loading={loading}
                slots={{
                    loadingOverlay: LinearProgress,
                }}
                getRowId={(row) => row.id}
                sx={{ 
                    '& .MuiDataGrid-cell:focus': { outline: 'none' },
                    minHeight: 400 
                }}
            />
        </Paper>
    );
}

// FIXED: Correct propTypes
RAGSessionsTable.propTypes = {
  handleOpenNewSessionModal: PropTypes.func.isRequired,
  onSessionSelect: PropTypes.func,
  updateTableFlag: PropTypes.bool.isRequired,
  setUpdateTableFlag: PropTypes.func.isRequired
};

export default RAGSessionsTable;