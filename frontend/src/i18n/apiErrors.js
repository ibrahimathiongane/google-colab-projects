/**
 * Maps the (English) messages returned by the API to translated strings.
 *
 * The backend contract stays untouched: we match on the known messages
 * and fall back to the raw text for anything new, so a new backend error
 * is never swallowed.
 */
const RULES = [
  ["Invalid credentials", "invalidCredentials"],
  ["Too many attempts", "rateLimited"],
  ["This email cannot be used", "emailTaken"],
  ["at least 8 characters", "passwordTooShort"],
  ["Invalid or expired reset link", "resetLinkInvalid"],
  ["upgrade to Pro", "upgradeRequired"],
  ["Notifications are not configured", "remindersNotConfigured"],
  ["Invalid refresh token", "sessionExpired"],
  ["Authentication required", "sessionExpired"],
  ["database unavailable", "server"],
  ["Habit not found", "notFound"],
  ["User not found", "notFound"],
];

export function translateApiError(t, message = "") {
  const text = String(message);
  for (const [match, key] of RULES) {
    if (text.includes(match)) return t(`errors.${key}`);
  }
  return text;
}
