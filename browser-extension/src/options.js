// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

/** @typedef {import('./types.js').Options} Options */

import { DEFAULT_OPTIONS, loadOptions, storeOptions, testCredentials } from "./legadilo.js";
import { getDialogById, getElementById, getFormById, getInputById } from "./typing-utils.js";

/**
 * @param {SubmitEvent} event
 * @returns {Promise<void>}
 */
const saveOptions = async (event) => {
  event.preventDefault();
  const data = new FormData(/** @type {HTMLFormElement} */ (event.target));

  await storeOptions({
    instanceUrl: /** @type {string} */ (data.get("instance-url")),
    userEmail: /** @type {string} */ (data.get("user-email")),
    tokenId: /** @type {string} */ (data.get("token-id")),
    tokenSecret: /** @type {string} */ (data.get("token-secret")),
  });

  // Update status to let user know options were saved.
  displayMessage("Options saved.");
};

/**
 * @param {string} text
 * @returns {void}
 */
const displayMessage = (text) => {
  const status = getElementById("status");
  status.textContent = text;
  setTimeout(() => {
    status.textContent = "";
  }, 5_000);
};

/**
 * @returns {Promise<void>}
 */
const restoreOptions = async () => {
  const options = await loadOptions();

  setOptions(options);
};

/**
 * @param {Partial<Options>} options
 * @returns {void}
 */
const setOptions = (options = {}) => {
  getInputById("instance-url").value = options.instanceUrl ?? "";
  getInputById("user-email").value = options.userEmail ?? "";
  getInputById("token-id").value = options.tokenId ?? "";
  getInputById("token-secret").value = options.tokenSecret ?? "";
};

/**
 * @returns {Promise<void>}
 */
const resetOptions = async () => {
  if (await askConfirmation()) {
    setOptions(DEFAULT_OPTIONS);
  }
};

/**
 * @returns {Promise<void>}
 */
const testOptions = async () => {
  const data = new FormData(getFormById("options-form"));

  if (
    await testCredentials({
      instanceUrl: /** @type {string} */ (data.get("instance-url")),
      userEmail: /** @type {string} */ (data.get("user-email")),
      tokenId: /** @type {string} */ (data.get("token-id")),
      tokenSecret: /** @type {string} */ (data.get("token-secret")),
    })
  ) {
    displayMessage("Instance URL and token are valid");
  } else {
    displayMessage("Failed to connect with supplied URL and tokens");
  }
};

/**
 * @returns {Promise<boolean>}
 */
const askConfirmation = () => {
  const confirmDialog = getDialogById("confirm-dialog");
  const abortController = new AbortController();

  const deferred = /** @type {Promise<boolean>} */ (
    new Promise((resolve, reject) => {
      confirmDialog.addEventListener(
        "click",
        (event) => {
          const target = /** @type {HTMLElement} */ (event.target);
          switch (target.id) {
            case "confirm-dialog-cancel-btn":
              confirmDialog.close();
              abortController.abort();
              resolve(false);
              break;
            case "confirm-dialog-confirm-btn":
              confirmDialog.close();
              abortController.abort();
              resolve(true);
              break;
            default:
              reject(new Error(`Unexpected click target: ${target.id}`));
          }
        },
        { signal: abortController.signal },
      );
    })
  );

  confirmDialog.showModal();

  return deferred;
};

addEventListener("DOMContentLoaded", () => {
  restoreOptions();
  const optionsForm = getFormById("options-form");
  optionsForm.addEventListener("submit", saveOptions);
  optionsForm.addEventListener("click", async (event) => {
    const target = /** @type {HTMLButtonElement} */ (event.target);
    switch (target.id) {
      case "reset-options":
        await resetOptions();
        break;
      case "test-options":
        await testOptions();
        break;
      default:
        if (target.type !== "submit") throw new Error(`Unexpected click target: ${target.id}`);
    }
  });
});
