import * as authApi from "../../../api/auth";
import { MOCK_USERS } from "./mockInstance";

/**
 * Session service. The logged-in user, login, registration, profile edits and
 * password changes go to the backend (/api/v1/auth), which keeps the session
 * in an httpOnly cookie. Backend users are translated to the shape the views
 * already use (camelCase, nickname, globalRole as a name).
 *
 * The list of every account shown in the admin views is still mock data in
 * localStorage, because the backend has no user administration endpoints yet.
 */

/**
 * Translate a user from the API into the shape used by the views.
 */
function toSessionUser(apiUser) {
  return {
    id: apiUser.id,
    email: apiUser.email,
    nickname: apiUser.username,
    socialName: apiUser.social_name,
    legalName: apiUser.legal_name ?? "",
    bio: apiUser.bio ?? "",
    phone: apiUser.phone ?? "",
    github: apiUser.github ?? "",
    linkedin: apiUser.linkedin ?? "",
    organization: apiUser.organization ?? "",
    position: apiUser.position ?? "",
    globalRole: apiUser.global_role.name,
    permissions: apiUser.permissions,
    // The backend refuses sessions of disabled accounts
    active: true,
  };
}

// Profile fields the backend lets a user edit, as view key -> API key
const PROFILE_FIELDS = {
  socialName: "social_name",
  bio: "bio",
  phone: "phone",
  github: "github",
  linkedin: "linkedin",
};

const MESSAGES = {
  "Invalid credentials": "Correo, nickname o contraseña incorrectos.",
  "This account is disabled":
    "Esta cuenta está desactivada. Contacta a un administrador.",
  "That username is already registered": "Ese nickname ya está en uso.",
  "That email is already registered": "Ya existe una cuenta con ese correo.",
  "That username or email is already registered":
    "Ese nickname o correo ya está registrado.",
  "The current password is incorrect": "La contraseña actual no es correcta.",
  "Accounts cannot be created yet":
    "Todavía no se pueden crear cuentas. Intenta más tarde.",
};

/**
 * Turn an API error into an Error with a message for the user.
 */
function toUserError(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string" && MESSAGES[detail]) {
    return new Error(MESSAGES[detail]);
  }
  if (error.response?.status === 422) {
    return new Error("Revisa los datos ingresados.");
  }
  if (!error.response) {
    return new Error("No se pudo conectar con el servidor.");
  }
  return new Error("Ocurrió un error inesperado. Intenta nuevamente.");
}

async function callApi(request) {
  try {
    return await request();
  } catch (error) {
    throw toUserError(error);
  }
}

export async function getCurrentUser() {
  try {
    return toSessionUser(await authApi.getMe());
  } catch (error) {
    // 401 only means there is no session; anything else is a real failure
    if (error.response?.status === 401) return null;
    throw toUserError(error);
  }
}

export async function login(identifier, password) {
  return toSessionUser(
    await callApi(() => authApi.login(identifier, password)),
  );
}

export async function logout() {
  await callApi(() => authApi.logout());
}

export async function register({ name, nickname, email, password }) {
  return toSessionUser(
    await callApi(() =>
      authApi.register({
        username: nickname,
        email,
        password,
        social_name: name,
      }),
    ),
  );
}

/**
 * Save changes to the logged-in user's own profile.
 */
export async function updateProfile(changes) {
  const unsupported = Object.keys(changes).filter(
    (key) => !(key in PROFILE_FIELDS),
  );
  if (unsupported.length > 0) {
    throw new Error("Este dato todavía no se puede modificar.");
  }

  const payload = Object.fromEntries(
    Object.entries(changes).map(([key, value]) => [PROFILE_FIELDS[key], value]),
  );
  return toSessionUser(await callApi(() => authApi.updateMe(payload)));
}

export async function changePassword(currentPassword, newPassword) {
  await callApi(() => authApi.changePassword(currentPassword, newPassword));
}

/* ==========================================================================
 * Mock accounts for the admin views. Replace with the user administration
 * endpoints once they exist.
 * ========================================================================== */

const USERS_KEY = "dashai-demo-users";

function readStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage unavailable (private mode, quota): changes last until reload
  }
}

// The password never leaves this module
function toPublicUser(user) {
  const publicUser = { ...user };
  delete publicUser.password;
  return publicUser;
}

function loadUsers() {
  return readStorage(USERS_KEY, MOCK_USERS);
}

export async function getUsers() {
  return loadUsers().map(toPublicUser);
}

export async function updateUser(userId, changes) {
  const safeChanges = { ...changes };
  delete safeChanges.password;

  const users = loadUsers().map((user) =>
    user.id === userId ? { ...user, ...safeChanges } : user,
  );
  writeStorage(USERS_KEY, users);
  return users.map(toPublicUser);
}

/**
 * Drops every change made to the mock accounts and goes back to MOCK_USERS.
 * Used by the debug tools of the login view.
 */
export async function resetDemoData() {
  writeStorage(USERS_KEY, null);
}
