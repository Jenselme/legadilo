/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/**
 * @param {string} id
 * @returns {HTMLElement}
 */
export const getElementById = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

/**
 * @param {string} id
 * @returns {HTMLInputElement}
 */
export const getInputById = (id) => /** @type {HTMLInputElement} */ (document.getElementById(id));

/**
 * @param {string} id
 * @returns {HTMLDialogElement}
 */
export const getDialogById = (id) => /** @type {HTMLDialogElement} */ (document.getElementById(id));

/**
 * @param {string} id
 * @returns {HTMLFormElement}
 */
export const getFormById = (id) => /** @type {HTMLFormElement} */ (document.getElementById(id));

/**
 * @param {string} selector
 * @returns {HTMLInputElement}
 */
export const getInputElementById = (selector) =>
  /** @type {HTMLInputElement} */ (document.getElementById(selector));

/**
 * @param {string} id
 * @returns {HTMLSelectElement}
 */
export const getSelectElementById = (id) =>
  /** @type {HTMLSelectElement} */ (document.getElementById(id));

/**
 * @param {string} id
 * @returns {HTMLAnchorElement}
 */
export const getLinkElementById = (id) =>
  /** @type {HTMLAnchorElement} */ (document.getElementById(id));
