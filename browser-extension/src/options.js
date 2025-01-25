import { DEFAULT_OPTIONS, loadOptions, storeOptions, testCredentials } from "./legadilo.js";

/**
 * @param event {SubmitEvent}
 */
const saveOptions = async (event) => {
  event.preventDefault();
  const data = new FormData(event.target);

  await storeOptions({
    instanceUrl: data.get("instance-url"),
    userEmail: data.get("user-email"),
    tokenId: data.get("token-id"),
    tokenSecret: data.get("token-secret"),
  });

  // Update status to let user know options were saved.
  displayMessage("Options saved.");
};

const displayMessage = (text) => {
  const status = document.getElementById("status");
  status.textContent = text;
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
  document.getElementById("user-email").value = options.userEmail;
  document.getElementById("token-id").value = options.tokenId;
  document.getElementById("token-secret").value = options.tokenSecret;
};

const resetOptions = () => {
  setOptions(DEFAULT_OPTIONS);
};

const testOptions = async () => {
  const data = new FormData(document.getElementById("options-form"));

  if (
    await testCredentials({
      instanceUrl: data.get("instance-url"),
      userEmail: data.get("user-email"),
      tokenId: data.get("token-id"),
      tokenSecret: data.get("token-secret"),
    })
  ) {
    displayMessage("Instance URL and token are valid");
  } else {
    displayMessage("Failed to connect with supplied URL and tokens");
  }
};

document.addEventListener("DOMContentLoaded", restoreOptions);
document.getElementById("options-form").addEventListener("submit", saveOptions);
document.getElementById("reset-options").addEventListener("click", resetOptions);
document.getElementById("test-options").addEventListener("click", testOptions);
