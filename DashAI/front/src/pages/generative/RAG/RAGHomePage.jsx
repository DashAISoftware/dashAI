import React from "react";

import NewSessionModal from "./NewSessionModal";
import RAGSessionsTable from "./RAGSessionsTable.jsx";

import CustomLayout from "../../../components/custom/CustomLayout.jsx";

function RAGHomePage({
    handleAddSession,
    selectedTaskName,
    setSelectedSessionId
    }) {
    const [showNewSessionModal, setShowNewSessionModal] = React.useState(false);
    const [updateTableFlag, setUpdateTableFlag] = React.useState(false);
    const [selectedSession, setSelectedSession] = React.useState(null);

    const handleOpenNewSessionModal = () => {
        setSelectedSession(null);
        setShowNewSessionModal(true);
    }

    const handleSessionSelect = (session) => {
        setSelectedSession(session);
        setShowNewSessionModal(true);
        setSelectedSessionId(session.id);
    }

    return (
        <CustomLayout
            title="RAG Sessions"
            subtitle="Manage your RAG sessions"
        >
            {showNewSessionModal? (
                <NewSessionModal
                    open={showNewSessionModal}
                    setOpen={setShowNewSessionModal}
                    setUpdateTableFlag={setUpdateTableFlag}
                    setSelectedSessionId={setSelectedSessionId}
                    handleAddSession={handleAddSession}
                    selectedSession={selectedSession}
                />
            ):(
                <RAGSessionsTable
                    handleOpenNewSessionModal={handleOpenNewSessionModal}
                    onSessionSelect={handleSessionSelect}
                    updateTableFlag={updateTableFlag}
                    setUpdateTableFlag={setUpdateTableFlag}
                />
            )
            }
        </CustomLayout>
    );
}

export default RAGHomePage;