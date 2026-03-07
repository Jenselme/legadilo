/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { vi } from "vitest";

// Mock the chrome global object
/* eslint-disable-next-line no-undef */
global.chrome = {
  storage: {
    local: {
      get: vi.fn(),
      set: vi.fn(),
    },
  },
};

// Mock fetch
/* eslint-disable-next-line no-undef */
global.fetch = vi.fn();

// Mock console.error to keep the test output clean
vi.spyOn(console, "error").mockImplementation(() => {});
