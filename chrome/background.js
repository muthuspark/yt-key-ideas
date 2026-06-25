chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id || !tab.url || !tab.url.includes("youtube.com/watch")) {
    return;
  }

  try {
    await chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_KEY_IDEAS_PANEL" });
  } catch {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["marked.umd.js", "content.js"],
    });
    await chrome.tabs.sendMessage(tab.id, { type: "TOGGLE_KEY_IDEAS_PANEL" });
  }
});
