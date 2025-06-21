// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  "use strict";

  // It is defined here and not as HTML attribute to avoid editing base.html for something that is
  // only useful or article details.
  // It's currently bug regarding progression display: https://github.com/Jenselme/legadilo/issues/248
  new bootstrap.ScrollSpy(document.body, {
    target: "#article-toc",
  });
})();
