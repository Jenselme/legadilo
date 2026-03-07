/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * Extracts the expiration time from a JWT.
 *
 * @param {string} token The JWT string.
 * @returns {Date|null} The expiration time as a Date, or null if not present or token is invalid.
 */
function getJwtExpirationTime(token) {
  try {
    const payload = token.split(".")[1];
    // Decode from URL safe base64 to JSON.
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    if (decoded.exp === undefined) {
      return null;
    }
    return new Date(decoded.exp * 1000);
  } catch {
    return null;
  }
}

/**
 * Returns true if the token is expired or will expire within the next 5 minutes.
 *
 * @param {string} token The JWT string.
 * @returns {boolean}
 */
export function mustJwtBeRenewed(token) {
  const TOKEN_EXPIRY_BUFFER_MS = 5 * 60 * 1000;
  const expirationDate = getJwtExpirationTime(token);
  if (!expirationDate) {
    return true;
  }
  return expirationDate < new Date(Date.now() + TOKEN_EXPIRY_BUFFER_MS);
}
