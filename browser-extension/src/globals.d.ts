/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

// Firefox provides `browser` as a global alias for `chrome` with a promise-based API.
declare const browser: typeof chrome | undefined;
