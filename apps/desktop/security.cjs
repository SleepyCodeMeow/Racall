const { session, shell } = require('electron');

/** Keep credentials and response policy in the main process's trusted session. */
function createSecureSession(origin, token) {
  const partition = session.fromPartition('persist:open-notebook');
  partition.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  // Scope the bearer header to this launch's loopback service, not external URLs.
  partition.webRequest.onBeforeSendHeaders({ urls: [origin + '/*'] }, (details, callback) => {
    details.requestHeaders.Authorization = `Bearer ${token}`;
    callback({ requestHeaders: details.requestHeaders });
  });
  partition.webRequest.onHeadersReceived((details, callback) => {
    const headers = { ...details.responseHeaders };
    if (!process.env.OPENNOTEBOOK_DEV_URL)
      headers['Content-Security-Policy'] = [
        `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-src blob: 'self'; object-src 'none'; base-uri 'none'; form-action 'none'`,
      ];
    callback({ responseHeaders: headers });
  });
  return partition;
}

/** Every privileged IPC must originate from this window and its trusted UI URL. */
function assertTrustedSender(event, window, uiOrigin) {
  if (
    !window ||
    event.sender !== window.webContents ||
    !event.senderFrame?.url.startsWith(uiOrigin + '/')
  ) {
    throw new Error('Untrusted sender');
  }
}

function protectNavigation(window, uiOrigin) {
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  window.webContents.on('will-navigate', (event, url) => {
    if (new URL(url).origin !== uiOrigin) event.preventDefault();
  });
}

module.exports = { createSecureSession, assertTrustedSender, protectNavigation };
