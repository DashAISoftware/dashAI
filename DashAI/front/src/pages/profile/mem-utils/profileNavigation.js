import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import ManageAccountsOutlinedIcon from "@mui/icons-material/ManageAccountsOutlined";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";

/**
 * Navigation entries of the profile sidebar, grouped by section.
 */
export const PROFILE_SIDEBAR = [
  {
    key: "account",
    label: "Cuenta",
    links: [
      {
        key: "profile",
        label: "Mi perfil",
        href: "/app/profile",
        Icon: PersonOutlineIcon,
      },
      {
        key: "manageAccount",
        label: "Gestionar cuenta",
        href: "/app/profile/account",
        Icon: ManageAccountsOutlinedIcon,
      },
    ],
  },
  {
    key: "projects",
    label: "Proyectos",
    links: [
      {
        key: "projects",
        label: "Mis proyectos",
        href: "/app/profile/projects",
        Icon: FolderOutlinedIcon,
      },
      {
        key: "requests",
        label: "Mis solicitudes",
        href: "/app/profile/requests",
        Icon: AssignmentOutlinedIcon,
      },
    ],
  },
];
