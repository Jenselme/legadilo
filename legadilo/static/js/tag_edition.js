import Tags from "/static/tags.js";

let tagsInstances;

const setupTagsInstance = () => {
  const potentialTagsElements = document.querySelectorAll("[data-bs5-tags=true]");
  if (potentialTagsElements.length === 0) {
    return;
  }

  if (tagsInstances) {
    tagsInstances.forEach((tagInstance) => tagInstance.dispose());
  }

  tagsInstances = Array.from(potentialTagsElements).map((tagElement) => {
    return new Tags(tagElement, { allowClear: true });
  });
};

document.addEventListener("DOMContentLoaded", setupTagsInstance);

document.addEventListener("htmx:afterSwap", setupTagsInstance);
