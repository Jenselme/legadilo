// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { getElementById, getInputById } from "./typing-utils.js";

vi.mock("./legadilo.js", () => ({
  DEFAULT_OPTIONS: {
    instanceUrl: "https://www.legadilo.eu",
    userEmail: "",
    tokenId: "",
    tokenSecret: "",
    accessToken: "",
  },
  loadOptions: vi.fn(),
  storeOptions: vi.fn(),
  testCredentials: vi.fn(),
}));
vi.mock("./i18n.js", () => ({ applyI18n: vi.fn() }));

import { __test__ } from "./options.js";
const { displayMessage, setOptions } = __test__;

function setupOptionsDom() {
  document.body.innerHTML = `
    <input id="instance-url" />
    <input id="user-email" />
    <input id="token-id" />
    <input id="token-secret" />
    <span id="status"></span>
  `;
}

describe("setOptions", () => {
  beforeEach(setupOptionsDom);
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("fills all inputs from a full options object", () => {
    setOptions({
      instanceUrl: "https://my.instance.com",
      userEmail: "user@example.com",
      tokenId: "tid-123",
      tokenSecret: "sec-456",
    });
    expect(getInputById("instance-url").value).toBe("https://my.instance.com");
    expect(getInputById("user-email").value).toBe("user@example.com");
    expect(getInputById("token-id").value).toBe("tid-123");
    expect(getInputById("token-secret").value).toBe("sec-456");
  });

  it("uses empty strings for missing properties", () => {
    setOptions({});
    expect(getInputById("instance-url").value).toBe("");
    expect(getInputById("user-email").value).toBe("");
    expect(getInputById("token-id").value).toBe("");
    expect(getInputById("token-secret").value).toBe("");
  });

  it("uses empty strings when called with no argument", () => {
    setOptions();
    expect(getInputById("instance-url").value).toBe("");
  });

  it("overwrites previously set values", () => {
    setOptions({ instanceUrl: "https://first.com" });
    setOptions({ instanceUrl: "https://second.com" });
    expect(getInputById("instance-url").value).toBe("https://second.com");
  });
});

describe("displayMessage", () => {
  beforeEach(() => {
    setupOptionsDom();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("sets the status text immediately", () => {
    displayMessage("Options saved");
    expect(getElementById("status").textContent).toBe("Options saved");
  });

  it("clears the status text after 5 seconds", () => {
    displayMessage("Options saved");
    vi.advanceTimersByTime(5000);
    expect(getElementById("status").textContent).toBe("");
  });

  it("does not clear before 5 seconds have passed", () => {
    displayMessage("Hello");
    vi.advanceTimersByTime(4999);
    expect(getElementById("status").textContent).toBe("Hello");
  });
});
