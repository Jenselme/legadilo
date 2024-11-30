import { DEFAULT_OPTIONS, loadOptions, storeOptions } from "./legadilo.js";

/**
 * @param event {SubmitEvent}
 */
const saveOptions = async (event) => {
  event.preventDefault();
  const data = new FormData(event.target);

  await storeOptions({
    instanceUrl: data.get("instanceUrl"),
    applicationToken: data.get("applicationToken"),
  });

  // Update status to let user know options were saved.
  const status = document.getElementById("status");
  status.textContent = "Options saved.";
  setTimeout(() => {
    status.textContent = "";
  }, 750);
};

const restoreOptions = async () => {
  const options = await loadOptions();

  setOptions(options);
};

const setOptions = (options = {}) => {
  document.getElementById("instance-url").value = options.instanceUrl;
  document.getElementById("application-token").value = options.applicationToken;
};

const resetOptions = () => {
  setOptions(DEFAULT_OPTIONS);
};

document.addEventListener("DOMContentLoaded", restoreOptions);
document.getElementById("options-form").addEventListener("submit", saveOptions);
document.getElementById("reset-options").addEventListener("click", resetOptions);
