import Tags from "/static/tags.js";

let tagsInstance;

const setupTagsInstance = () => {
  const potentialTagsElements = document.querySelectorAll("[data-bs5-tags=true]");
  if (potentialTagsElements.length === 0) {
    return;
  }

  if (potentialTagsElements.length > 1) {
    console.error("We do not support multiple tag instances on HTMX powered pages!");
    return;
  }

  if (tagsInstance) {
    tagsInstance.dispose();
  }

  tagsInstance = new Tags(potentialTagsElements[0], { allowClear: true });
};

document.addEventListener("DOMContentLoaded", setupTagsInstance);

document.addEventListener("htmx:afterSwap", setupTagsInstance);
