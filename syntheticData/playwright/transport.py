"""Observe actual tracking fetches, including requests not yet routed by Python."""

OBSERVE_TRACKING = """(() => {
    const originalFetch = window.fetch.bind(window);
    const pending = new Set();
    window.__tikitPendingTracking = pending;
    window.fetch = function(...args) {
        const promise = originalFetch(...args);
        const url = String(args[0]?.url ?? args[0]);
        if (url.includes('/tracking/events')) {
            pending.add(promise);
            promise.then(() => pending.delete(promise), () => pending.delete(promise));
        }
        return promise;
    };
})()"""

DRAIN_TRACKING = """async () => {
    await new Promise(resolve => setTimeout(resolve, 0));
    const pending = window.__tikitPendingTracking;
    if (!pending) throw new Error('Tracking transport observer not installed');
    while (pending.size) await Promise.allSettled([...pending]);
}"""
