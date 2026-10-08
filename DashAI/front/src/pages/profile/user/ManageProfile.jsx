import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import ProfileLayout from "../mem-utils/ProfileLayout";
import { MOCK_USER } from "../mem-utils/mockUser";
import ManageProfileContent from "../utils/ManageProfileContent";
import { EmailRequestForm, NicknameForm } from "../utils/AccountForms";

export default function ManageProfile() {
  const navigate = useNavigate();
  const [user, setUser] = useState(MOCK_USER);
  const [pendingEmail, setPendingEmail] = useState(null);
  // Key of the form shown in the right panel, or null when closed
  const [activeForm, setActiveForm] = useState(null);

  const closeForm = () => setActiveForm(null);

  // Changing the password has its own view; the rest open in the panel
  const handleEdit = (key) =>
    key === "password" ? navigate("/app/profile/password") : setActiveForm(key);

  const forms = {
    nickname: (
      <NicknameForm
        nickname={user.nickname}
        onSave={(nickname) =>
          setUser((previous) => ({ ...previous, nickname }))
        }
        onClose={closeForm}
      />
    ),
    email: (
      <EmailRequestForm
        currentEmail={user.email}
        pendingEmail={pendingEmail}
        onSubmit={setPendingEmail}
        onClose={closeForm}
      />
    ),
  };

  return (
    <ProfileLayout
      title="Gestionar cuenta"
      subtitle="Administra los datos sensibles de tu cuenta y solicita cambios en la información gestionada por tu organización."
      contentSx={{ px: { xs: 3, sm: 4, md: 6 }, py: 5 }}
      rightPanel={activeForm ? forms[activeForm] : null}
    >
      <ManageProfileContent
        user={user}
        pendingEmail={pendingEmail}
        onEdit={handleEdit}
      />
    </ProfileLayout>
  );
}
