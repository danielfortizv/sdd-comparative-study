export function startRefreshPolling(refresh, intervalMs = 5000) {
  const timer = globalThis.setInterval(refresh, intervalMs);
  return () => globalThis.clearInterval(timer);
}
