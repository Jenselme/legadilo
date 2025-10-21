// SPDX-FileCopyrightText: 2023-2025 Legadilo contributors
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
  let dragged = null;
  let dropTarget = null;
  let saveRequest = Promise.resolve();
  const successToast = bootstrap.Toast.getOrCreateInstance(
    document.getElementById("reading-lists-reordered"),
  );
  const errorToast = bootstrap.Toast.getOrCreateInstance(
    document.getElementById("reading-lists-reorder-error"),
  );
  const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value;

  document.querySelectorAll('[draggable="true"]').forEach((draggable) => {
    draggable.addEventListener("dragstart", () => {
      dragged = draggable;
      dragged.classList.add("dragged");
    });

    draggable.addEventListener("dragenter", (event) => {
      event.preventDefault();
      const potentialDropTarget = event.target.closest('[draggable="true"]');
      if (potentialDropTarget === dragged || potentialDropTarget === dropTarget) return;

      if (dropTarget) dropTarget.classList.remove("dragged-over");
      dropTarget = potentialDropTarget;
      dropTarget.classList.add("dragged-over");
    });

    draggable.addEventListener("dragleave", (event) => {
      const draggableParent = event.target.closest('[draggable="true"]');
      if (!dropTarget || draggableParent === dropTarget) return;
      dropTarget.classList.remove("dragged-over");
      dropTarget = null;
    });

    draggable.addEventListener("dragover", (event) => {
      event.preventDefault();
    });

    draggable.addEventListener("dragend", () => {
      dragged.classList.remove("dragged");
      dragged = null;
    });

    draggable.addEventListener("drop", () => {
      if (!dropTarget || !dragged) return;

      const container = dragged.parentElement;
      let currentPos = 0;
      let dropPos = 0;
      container.querySelectorAll('[draggable="true"]').forEach((draggable, index) => {
        if (draggable === dropTarget) {
          dropPos = index;
        }
        if (draggable === dragged) {
          currentPos = index;
        }
      });

      if (currentPos < dropPos) {
        container.insertBefore(dragged, dropTarget.nextSibling);
      } else {
        container.insertBefore(dragged, dropTarget);
      }

      dropTarget.classList.remove("dragged-over");
      dragged.classList.remove("dragged");

      const reorderedReadingLists = Array.from(
        container.querySelectorAll('[draggable="true"]'),
      ).reduce(
        (acc, readingList, index) => ({ ...acc, [readingList.dataset.readingListId]: index }),
        {},
      );
      saveRequest = saveRequest
        .then(() =>
          fetch("/api/reading/lists/reorder/", {
            "Content-Type": "application/json",
            headers: {
              "X-CSRFToken": csrftoken,
            },
            method: "POST",
            body: JSON.stringify({ order: reorderedReadingLists }),
          }),
        )
        .then((response) => {
          console.log(response, response.ok);
          if (!response.ok) {
            return Promise.reject(new Error("Failed to reorder reading lists"));
          }
        })
        .then(
          () => {
            successToast.show();
          },
          () => {
            errorToast.show();
          },
        );
    });
  });
})();
