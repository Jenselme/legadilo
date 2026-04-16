/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

import { vi } from "vitest";

// Mock the chrome global object
/* eslint-disable-next-line no-undef */
global.chrome = /** @type {typeof chrome} */ (
  /** @type {unknown} */ ({
    runtime: {
      onInstalled: { addListener: vi.fn() },
      onMessage: { addListener: vi.fn() },
      onConnect: { addListener: vi.fn() },
    },
    contextMenus: {
      create: vi.fn(),
      update: vi.fn(),
      onClicked: { addListener: vi.fn() },
    },
    tabs: {
      get: vi.fn(),
      onActivated: { addListener: vi.fn() },
      onUpdated: { addListener: vi.fn() },
    },
    action: {
      enable: vi.fn(),
      disable: vi.fn(),
    },
    storage: {
      local: {
        get: vi.fn(),
        set: vi.fn(),
      },
    },
  })
);

// Mock fetch
/* eslint-disable-next-line no-undef */
global.fetch = vi.fn();

// Mock console.error to keep the test output clean
vi.spyOn(console, "error").mockImplementation(() => {});
