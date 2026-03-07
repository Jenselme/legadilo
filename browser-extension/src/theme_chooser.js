/*
 * SPDX-FileCopyrightText: 2026 Legadilo contributors
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

// Color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
// https://getbootstrap.com/docs/5.3/customize/color-modes/#javascript

(() => {
  "use strict";

  const setTheme = () => {
    const theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.setAttribute("data-bs-theme", theme);
  };

  setTheme();

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    setTheme();
  });
})();
