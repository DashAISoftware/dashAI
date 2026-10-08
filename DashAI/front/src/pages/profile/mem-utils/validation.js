/**
 * Validation rules shared by the account and session forms.
 */
export const NICKNAME_PATTERN = /^[a-zA-Z0-9_.]{3,20}$/;
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const MIN_PASSWORD_LENGTH = 8;
