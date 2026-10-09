// The chalktalk designer moved to /chalktalk-designer/. A browser that installed
// it here checks this file for a new version, so this worker takes the old one's
// place: it clears the old offline copy, sends any open window to the new
// address, and unregisters itself. The moved app keeps its own cache, named
// chalktalk-designer-, on the same origin; leave that one alone.
self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    await self.clients.claim();
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k.startsWith("chalktalk-") && !k.startsWith("chalktalk-designer-"))
                          .map(k => caches.delete(k)));
    const windows = await self.clients.matchAll({type: "window"});
    await Promise.all(windows.map(w =>
      w.navigate(w.url.replace("/chalktalk/", "/chalktalk-designer/")).catch(() => null)));
    await self.registration.unregister();
  })());
});
