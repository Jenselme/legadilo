// Legadilo
// Copyright (C) 2023-2025 by Legadilo contributors.
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
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import Tags from "/static/tags.js";

let tagsInstances;

const setupTagsInstance = () => {
  const potentialTagsElements = document.querySelectorAll("[data-bs5-tags=true]");
  if (potentialTagsElements.length === 0) {
    return;
  }

  let tagsHierarchy = {};
  const tagsHierarchyElement = document.head.querySelector("#tags-hierarchy");
  if (tagsHierarchyElement !== null) {
    tagsHierarchy = JSON.parse(tagsHierarchyElement.textContent);
  }

  if (tagsInstances) {
    tagsInstances.forEach((tagInstance) => tagInstance.dispose());
  }

  tagsInstances = Array.from(potentialTagsElements).map((tagElement) => {
    return new Tags(tagElement, {
      allowClear: true,
      onSelectItem(item, instance) {
        if (!Array.isArray(tagsHierarchy[item.value])) {
          return;
        }

        const alreadyAddedItems = instance.getSelectedValues();
        tagsHierarchy[item.value]
          .filter((tag) => !alreadyAddedItems.includes(tag.slug))
          .forEach((tag) => instance.addItem(tag.title, tag.slug));
      },
    });
  });
};

document.addEventListener("DOMContentLoaded", setupTagsInstance);

document.addEventListener("htmx:afterSwap", setupTagsInstance);
