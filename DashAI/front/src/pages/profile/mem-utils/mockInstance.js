/**
 * Static instance-wide data used by the administration views until they are
 * connected to the backend. Permissions and roles mirror the catalog in
 * DashAI/back/auth/catalog.py, so keep both in sync.
 */

export const GLOBAL_ROLES = ["Administrador", "Miembro"];
export const PROJECT_ROLES = ["Dueño", "Gestor", "Colaborador", "Lector"];

// `instance` permissions only make sense in a global role
export const PERMISSIONS = [
  { uid: "datasets.read", category: "Datos", description: "Ver datasets" },
  {
    uid: "datasets.write",
    category: "Datos",
    description: "Crear y modificar datasets",
  },
  {
    uid: "datasets.delete",
    category: "Datos",
    description: "Eliminar datasets",
  },
  {
    uid: "datasets.export",
    category: "Datos",
    description: "Descargar datasets",
  },
  { uid: "notebooks.read", category: "Datos", description: "Ver notebooks" },
  {
    uid: "notebooks.write",
    category: "Datos",
    description: "Crear y modificar notebooks",
  },
  {
    uid: "models.read",
    category: "Modelos",
    description: "Ver sesiones y resultados",
  },
  {
    uid: "models.write",
    category: "Modelos",
    description: "Crear y modificar sesiones de modelos y pipelines",
  },
  {
    uid: "models.execute",
    category: "Modelos",
    description: "Entrenar modelos, ejecutar predicciones y explicaciones",
  },
  {
    uid: "models.delete",
    category: "Modelos",
    description: "Eliminar sesiones, runs y pipelines",
  },
  {
    uid: "generative.read",
    category: "Generativo",
    description: "Ver sesiones generativas",
  },
  {
    uid: "generative.execute",
    category: "Generativo",
    description: "Usar modelos generativos, incluidas las consultas RAG",
  },
  {
    uid: "generative.delete",
    category: "Generativo",
    description: "Eliminar sesiones generativas",
  },
  {
    uid: "documents.read",
    category: "Documentos",
    description: "Ver documentos",
  },
  {
    uid: "documents.write",
    category: "Documentos",
    description: "Subir, extraer y configurar documentos",
  },
  {
    uid: "documents.index",
    category: "Documentos",
    description: "Indexar documentos para RAG",
  },
  {
    uid: "documents.export",
    category: "Documentos",
    description: "Descargar documentos",
  },
  {
    uid: "documents.delete",
    category: "Documentos",
    description: "Eliminar documentos",
  },
  {
    uid: "projects.manage",
    category: "Proyecto",
    description: "Gestionar miembros y roles del proyecto",
  },
  {
    uid: "projects.oversee",
    category: "Instancia",
    description: "Gestionar todos los proyectos de la instancia",
    instance: true,
  },
  {
    uid: "users.manage",
    category: "Instancia",
    description: "Gestionar usuarios",
    instance: true,
  },
  {
    uid: "requests.review",
    category: "Instancia",
    description: "Revisar solicitudes de acceso",
    instance: true,
  },
  {
    uid: "roles.manage",
    category: "Instancia",
    description: "Gestionar roles y permisos",
    instance: true,
  },
  {
    uid: "instance.manage",
    category: "Instancia",
    description: "Gestionar plugins y actualizaciones",
    instance: true,
  },
];

const ALL_PERMISSIONS = PERMISSIONS.map((permission) => permission.uid);
const PROJECT_PERMISSIONS = PERMISSIONS.filter(
  (permission) => !permission.instance,
).map((permission) => permission.uid);

// `system` roles are fixed: their permissions follow a rule and cannot be
// edited. The others start with these defaults and can be changed.
export const MOCK_ROLES = [
  {
    id: "ROLE-ADMIN",
    name: "Administrador",
    scope: "Global",
    system: true,
    description: "Administra la instancia y accede a todos los proyectos.",
    permissions: ALL_PERMISSIONS,
  },
  {
    id: "ROLE-MEMBER",
    name: "Miembro",
    scope: "Global",
    system: false,
    description: "Usuario de la organización sin privilegios de gestión.",
    // Transitional, see the note in catalog.py
    permissions: PROJECT_PERMISSIONS.filter((uid) => uid !== "projects.manage"),
  },
  {
    id: "ROLE-OWNER",
    name: "Dueño",
    scope: "Proyecto",
    system: true,
    description: "Control total del proyecto, incluidos sus integrantes.",
    permissions: PROJECT_PERMISSIONS,
  },
  {
    id: "ROLE-MANAGER",
    name: "Gestor",
    scope: "Proyecto",
    system: false,
    description:
      "Crea y edita los recursos del proyecto, sin gestionar integrantes.",
    permissions: PROJECT_PERMISSIONS.filter((uid) => uid !== "projects.manage"),
  },
  {
    id: "ROLE-COLLABORATOR",
    name: "Colaborador",
    scope: "Proyecto",
    system: false,
    description:
      "Trabaja con los recursos del proyecto, sin eliminarlos ni descargarlos.",
    permissions: PROJECT_PERMISSIONS.filter(
      (uid) =>
        !uid.endsWith(".delete") &&
        !uid.endsWith(".export") &&
        uid !== "projects.manage",
    ),
  },
  {
    id: "ROLE-READER",
    name: "Lector",
    scope: "Proyecto",
    system: true,
    description: "Solo puede consultar el contenido del proyecto.",
    permissions: PROJECT_PERMISSIONS.filter((uid) => uid.endsWith(".read")),
  },
];

/**
 * Accounts available in the toy session. Passwords are stored in plain text
 * only because this is mock data; the real backend stores password hashes.
 */
export const MOCK_USERS = [
  {
    id: "USR-001",
    email: "juan.soto@example.com",
    password: "usuario123",
    legalName: "Juan Soto",
    socialName: "Juan Soto",
    nickname: "juansoto",
    bio: "Estudiante interesado en computación, desarrollo de software y aprendizaje automático.",
    phone: "+56 9 1234 5678",
    github: "github.com/juan-soto-demo",
    linkedin: "linkedin.com/in/juan-soto-demo",
    organization: "Universidad de Ejemplo",
    position: "Estudiante",
    globalRole: "Miembro",
    active: true,
  },
  {
    id: "USR-006",
    email: "carla.rojas@example.com",
    password: "admin123",
    legalName: "Carla Rojas",
    socialName: "Carla Rojas",
    nickname: "crojas",
    bio: "Encargada de la plataforma de ciencia de datos de la organización.",
    phone: "",
    github: "",
    linkedin: "",
    organization: "Universidad de Ejemplo",
    position: "Administradora de plataforma",
    globalRole: "Administrador",
    active: true,
  },
  {
    id: "USR-002",
    email: "ana.perez@example.com",
    password: "demo1234",
    legalName: "Ana Pérez",
    socialName: "Ana Pérez",
    nickname: "anaperez",
    bio: "",
    phone: "",
    github: "",
    linkedin: "",
    organization: "Universidad de Ejemplo",
    position: "Investigadora",
    globalRole: "Miembro",
    active: true,
  },
  {
    id: "USR-003",
    email: "pedro.munoz@example.com",
    password: "demo1234",
    legalName: "Pedro Muñoz",
    socialName: "Pedro Muñoz",
    nickname: "pmunoz",
    bio: "",
    phone: "",
    github: "",
    linkedin: "",
    organization: "Universidad de Ejemplo",
    position: "Ingeniero de datos",
    globalRole: "Miembro",
    active: true,
  },
  {
    id: "USR-004",
    email: "diego.rojas@example.com",
    password: "demo1234",
    legalName: "Diego Rojas",
    socialName: "Diego Rojas",
    nickname: "drojas",
    bio: "",
    phone: "",
    github: "",
    linkedin: "",
    organization: "Universidad de Ejemplo",
    position: "Estudiante",
    globalRole: "Miembro",
    active: true,
  },
  {
    id: "USR-005",
    email: "catalina.fuentes@example.com",
    password: "demo1234",
    legalName: "Catalina Fuentes",
    socialName: "Catalina Fuentes",
    nickname: "cfuentes",
    bio: "",
    phone: "",
    github: "",
    linkedin: "",
    organization: "Universidad de Ejemplo",
    position: "Analista",
    globalRole: "Miembro",
    active: false,
  },
];

export const MOCK_PROJECTS = [
  {
    id: "PRJ-001",
    name: "Proyecto de Machine Learning",
    ownerId: "USR-001",
    archived: false,
    members: [
      { userId: "USR-001", role: "Dueño" },
      { userId: "USR-002", role: "Colaborador" },
      { userId: "USR-003", role: "Gestor" },
    ],
  },
  {
    id: "PRJ-002",
    name: "Análisis de datasets",
    ownerId: "USR-002",
    archived: false,
    members: [
      { userId: "USR-002", role: "Dueño" },
      { userId: "USR-001", role: "Lector" },
      { userId: "USR-003", role: "Colaborador" },
    ],
  },
  {
    id: "PRJ-003",
    name: "Modelos generativos",
    ownerId: "USR-001",
    archived: false,
    members: [
      { userId: "USR-001", role: "Dueño" },
      { userId: "USR-004", role: "Colaborador" },
      { userId: "USR-005", role: "Lector" },
    ],
  },
  {
    id: "PRJ-004",
    name: "Clasificación de imágenes",
    ownerId: "USR-003",
    archived: false,
    members: [
      { userId: "USR-003", role: "Dueño" },
      { userId: "USR-004", role: "Colaborador" },
    ],
  },
  {
    id: "PRJ-005",
    name: "Piloto de encuestas",
    ownerId: "USR-005",
    archived: true,
    members: [{ userId: "USR-005", role: "Dueño" }],
  },
];

export const MOCK_REQUESTS = [
  {
    id: "REQ-001",
    subject: "Acceso de edición al proyecto",
    projectId: "PRJ-001",
    requesterId: "USR-001",
    status: "Pendiente",
    permissions: ["datasets.write", "models.execute", "models.write"],
    reason:
      "Necesito modificar los datasets utilizados por el workflow de entrenamiento.",
  },
  {
    id: "REQ-002",
    subject: "Acceso a modelos generativos",
    projectId: "PRJ-003",
    requesterId: "USR-001",
    status: "Aprobada",
    permissions: ["generative.read", "generative.execute"],
    reason:
      "Necesito utilizar las herramientas generativas disponibles en el proyecto.",
  },
  {
    id: "REQ-003",
    subject: "Permiso para modificar datasets",
    projectId: "PRJ-002",
    requesterId: "USR-001",
    status: "Rechazada",
    permissions: ["datasets.write"],
    reason:
      "Se requiere acceso de edición para preparar los datos del proyecto.",
  },
  {
    id: "REQ-004",
    subject: "Unirse al proyecto como lector",
    projectId: "PRJ-001",
    requesterId: "USR-004",
    status: "Pendiente",
    permissions: ["datasets.read", "models.read"],
    reason: "Quiero revisar los resultados del entrenamiento para mi informe.",
  },
  {
    id: "REQ-005",
    subject: "Ejecutar entrenamientos",
    projectId: "PRJ-004",
    requesterId: "USR-002",
    status: "Pendiente",
    permissions: ["models.execute"],
    reason: "Debo entrenar una nueva versión del clasificador de imágenes.",
  },
];

export function getUserName(userId) {
  return MOCK_USERS.find((user) => user.id === userId)?.socialName ?? userId;
}

export function getProjectName(projectId) {
  return (
    MOCK_PROJECTS.find((project) => project.id === projectId)?.name ?? projectId
  );
}

export function getRolePermissions(roleName) {
  return MOCK_ROLES.find((role) => role.name === roleName)?.permissions ?? [];
}

/**
 * Projects the user belongs to, in the shape used by "Mis proyectos".
 */
export function getUserProjects(userId) {
  return MOCK_PROJECTS.filter((project) =>
    project.members.some((member) => member.userId === userId),
  ).map((project) => {
    const role = project.members.find(
      (member) => member.userId === userId,
    ).role;
    return {
      id: project.id,
      name: project.name,
      role,
      owner: getUserName(project.ownerId),
      members: project.members.length,
      permissions: getRolePermissions(role).length,
      teamSummary: project.members
        .map((member) => getUserName(member.userId).split(" ")[0])
        .join(", "),
    };
  });
}

/**
 * Requests made by the user, in the shape used by "Mis solicitudes".
 */
export function getUserRequests(userId) {
  return MOCK_REQUESTS.filter((request) => request.requesterId === userId).map(
    (request) => ({
      id: request.id,
      subject: request.subject,
      project: request.projectId,
      status: request.status,
      requester: getUserName(request.requesterId),
      permissions: request.permissions,
      reason: request.reason,
    }),
  );
}
