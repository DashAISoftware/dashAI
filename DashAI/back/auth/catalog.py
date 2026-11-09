"""Built-in permissions and roles, synchronized with the database on startup.

Roles cannot be created or deleted: the six below always exist. Fixed roles
(``is_system``) get their permissions from a rule and are recomputed on every
startup, so new permissions reach them automatically. Editable roles are
created once with default permissions; after that the database wins, so an
administrator's edits are kept.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Tuple

from sqlalchemy import select

from DashAI.back.dependencies.database.models import Permission, Role

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PermissionSpec:
    uid: str
    name: str
    category: str
    # Instance permissions only make sense in a global role; the rest apply
    # inside a project
    instance: bool = False


# Each module follows the same pattern: read, write (create and edit), delete,
# execute for work that uses compute and export for taking data out
PERMISSIONS: List[PermissionSpec] = [
    PermissionSpec("datasets.read", "Ver datasets", "Datos"),
    PermissionSpec("datasets.write", "Crear y modificar datasets", "Datos"),
    PermissionSpec("datasets.delete", "Eliminar datasets", "Datos"),
    PermissionSpec("datasets.export", "Descargar datasets", "Datos"),
    PermissionSpec("notebooks.read", "Ver notebooks", "Datos"),
    PermissionSpec("notebooks.write", "Crear y modificar notebooks", "Datos"),
    PermissionSpec("models.read", "Ver sesiones y resultados", "Modelos"),
    PermissionSpec(
        "models.write", "Crear y modificar sesiones de modelos y pipelines", "Modelos"
    ),
    PermissionSpec(
        "models.execute",
        "Entrenar modelos, ejecutar predicciones y explicaciones",
        "Modelos",
    ),
    PermissionSpec("models.delete", "Eliminar sesiones, runs y pipelines", "Modelos"),
    PermissionSpec("generative.read", "Ver sesiones generativas", "Generativo"),
    PermissionSpec(
        "generative.execute",
        "Usar modelos generativos, incluidas las consultas RAG",
        "Generativo",
    ),
    PermissionSpec("generative.delete", "Eliminar sesiones generativas", "Generativo"),
    PermissionSpec("documents.read", "Ver documentos", "Documentos"),
    PermissionSpec(
        "documents.write", "Subir, extraer y configurar documentos", "Documentos"
    ),
    PermissionSpec("documents.index", "Indexar documentos para RAG", "Documentos"),
    PermissionSpec("documents.export", "Descargar documentos", "Documentos"),
    PermissionSpec("documents.delete", "Eliminar documentos", "Documentos"),
    PermissionSpec(
        "projects.manage", "Gestionar miembros y roles del proyecto", "Proyecto"
    ),
    PermissionSpec(
        "projects.oversee",
        "Gestionar todos los proyectos de la instancia",
        "Instancia",
        instance=True,
    ),
    PermissionSpec("users.manage", "Gestionar usuarios", "Instancia", instance=True),
    PermissionSpec(
        "requests.review", "Revisar solicitudes de acceso", "Instancia", instance=True
    ),
    PermissionSpec(
        "roles.manage", "Gestionar roles y permisos", "Instancia", instance=True
    ),
    PermissionSpec(
        "instance.manage",
        "Gestionar plugins y actualizaciones",
        "Instancia",
        instance=True,
    ),
]

ALL_PERMISSIONS = [p.uid for p in PERMISSIONS]
PROJECT_PERMISSIONS = [p.uid for p in PERMISSIONS if not p.instance]
READ_PERMISSIONS = [uid for uid in PROJECT_PERMISSIONS if uid.endswith(".read")]


@dataclass(frozen=True)
class RoleSpec:
    uid: str
    name: str
    description: str
    scope: str
    # Fixed roles cannot be edited; their permissions are recomputed from
    # the rule on every startup
    fixed: bool
    permissions: Callable[[], List[str]]


ROLES: List[RoleSpec] = [
    RoleSpec(
        "admin",
        "Administrador",
        "Administra la instancia y accede a todos los proyectos.",
        "global",
        fixed=True,
        permissions=lambda: ALL_PERMISSIONS,
    ),
    RoleSpec(
        "member",
        "Miembro",
        "Usuario de la organización sin privilegios de gestión.",
        "global",
        fixed=False,
        # Transitional: until resources belong to projects, the global role
        # is the only one checked, so members get every project permission
        # except managing other people. Once project roles are checked, this
        # must shrink back, or a project "Lector" could still write through
        # the global role.
        permissions=lambda: [
            uid for uid in PROJECT_PERMISSIONS if uid != "projects.manage"
        ],
    ),
    RoleSpec(
        "owner",
        "Dueño",
        "Control total del proyecto, incluidos sus integrantes.",
        "project",
        fixed=True,
        permissions=lambda: PROJECT_PERMISSIONS,
    ),
    RoleSpec(
        "manager",
        "Gestor",
        "Crea y edita los recursos del proyecto, sin gestionar integrantes.",
        "project",
        fixed=False,
        permissions=lambda: [
            uid for uid in PROJECT_PERMISSIONS if uid != "projects.manage"
        ],
    ),
    RoleSpec(
        "collaborator",
        "Colaborador",
        "Trabaja con los recursos del proyecto, sin eliminarlos ni descargarlos.",
        "project",
        fixed=False,
        permissions=lambda: [
            uid
            for uid in PROJECT_PERMISSIONS
            if not uid.endswith((".delete", ".export")) and uid != "projects.manage"
        ],
    ),
    RoleSpec(
        "reader",
        "Lector",
        "Solo puede consultar el contenido del proyecto.",
        "project",
        fixed=True,
        permissions=lambda: READ_PERMISSIONS,
    ),
]


def _sync_permissions(db) -> Dict[str, Permission]:
    """Create missing permissions and refresh the labels of existing ones."""
    existing = {p.uid: p for p in db.execute(select(Permission)).scalars()}

    for spec in PERMISSIONS:
        permission = existing.get(spec.uid)
        if permission is None:
            permission = Permission(uid=spec.uid)
            db.add(permission)
            existing[spec.uid] = permission
        permission.name = spec.name
        permission.category = spec.category

    # Never deleted automatically: roles may still reference them, so removing
    # one is left to whoever changes the catalog
    unknown = sorted(set(existing) - set(ALL_PERMISSIONS))
    if unknown:
        logger.warning("Permissions not in the catalog: %s.", ", ".join(unknown))

    return existing


def _sync_roles(db, permissions: Dict[str, Permission]) -> Tuple[int, int]:
    """Create missing roles and recompute the permissions of fixed ones."""
    existing = {r.uid: r for r in db.execute(select(Role)).scalars()}
    created = updated = 0

    for spec in ROLES:
        role = existing.get(spec.uid)
        is_new = role is None
        if is_new:
            role = Role(uid=spec.uid)
            db.add(role)
            created += 1

        role.name = spec.name
        role.description = spec.description
        role.scope = spec.scope
        role.is_system = spec.fixed

        # Editable roles keep whatever an administrator set after creation
        if is_new or spec.fixed:
            wanted = {permissions[uid] for uid in spec.permissions()}
            if set(role.permissions) != wanted:
                role.permissions = sorted(wanted, key=lambda p: p.uid)
                if not is_new:
                    updated += 1

    return created, updated


def sync_auth_catalog(session_factory: "sessionmaker") -> None:
    """Make the permissions and built-in roles in the database match the catalog.

    Safe to run on every startup: it only writes what differs.

    Parameters
    ----------
    session_factory : sessionmaker
        Factory of database sessions.
    """
    with session_factory() as db:
        try:
            permissions = _sync_permissions(db)
            db.flush()
            created, updated = _sync_roles(db, permissions)
            db.commit()
        except Exception:
            db.rollback()
            raise

    if created or updated:
        logger.info(
            "Auth catalog synced: %d roles created, %d fixed roles updated.",
            created,
            updated,
        )
