// Legadilo
// Copyright (C) 2023-2024 by Legadilo contributors.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

(function () {
  "use strict";

  // It is defined here and not as HTML attribute to avoid editing base.html for something that is
  // only useful or article details.
  new bootstrap.ScrollSpy(document.body, {
    target: "#article-toc",
  });
})();
