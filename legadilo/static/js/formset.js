// SPDX-FileCopyrightText: 2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  const formsetContainer = document.getElementById("formset-container");
  const addFormsetRow = formsetContainer.querySelector("#add-formset-row");
  const fieldsContainer = formsetContainer.querySelector("table tbody");
  const firstFormsetRow = formsetContainer.querySelector("table tbody tr.empty-form");
  const totalFormsetRows = formsetContainer.querySelector("#id_form-TOTAL_FORMS");

  const replacePrefix = (elt, index) => {
    const attributesToReplace = ["id", "name", "aria-describedby"];
    for (const attrName of attributesToReplace) {
      const attrValue = elt.getAttribute(attrName);
      if (!attrValue) continue;
      elt.setAttribute(attrName, attrValue.replace("__prefix__", index.toString()));
    }
  };

  addFormsetRow.addEventListener("click", () => {
    const newNodeIndex = parseInt(totalFormsetRows.value, 10);
    const newNode = firstFormsetRow.cloneNode(true);
    newNode.classList.remove("d-none", "empty-form");
    for (const child of newNode.children) {
      replacePrefix(child, newNodeIndex);

      for (const innerChild of child.children) {
        replacePrefix(innerChild, newNodeIndex);
      }
    }
    fieldsContainer.appendChild(newNode);
    totalFormsetRows.value = newNodeIndex + 1;
  });
})();
