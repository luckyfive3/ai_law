/**
 * vitest setup — mock browser globals
 */

// Ensure localStorage exists and is resettable
if (!globalThis.localStorage) {
  const store = {};
  globalThis.localStorage = {
    getItem: (key) => store[key] ?? null,
    setItem: (key, value) => { store[key] = String(value); },
    removeItem: (key) => { delete store[key]; },
  };
}

// Ensure sessionStorage exists
if (!globalThis.sessionStorage) {
  const sStore = {};
  globalThis.sessionStorage = {
    getItem: (key) => sStore[key] ?? null,
    setItem: (key, value) => { sStore[key] = String(value); },
    removeItem: (key) => { delete sStore[key]; },
  };
}

// Reset storage (call in beforeEach)
globalThis._resetStorage = () => {
  for (const k of Object.keys(localStorage)) {
    localStorage.removeItem(k);
  }
  for (const k of Object.keys(sessionStorage)) {
    sessionStorage.removeItem(k);
  }
};
