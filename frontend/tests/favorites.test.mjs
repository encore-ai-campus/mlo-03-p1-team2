import assert from 'node:assert/strict';
import { after, test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { createPinia, setActivePinia } from 'pinia';

const server = await createServer({
  configFile: false,
  optimizeDeps: { noDiscovery: true, include: [] },
  resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } },
  server: { middlewareMode: true },
  appType: 'custom',
});
after(() => server.close());
const { useAuthStore } = await server.ssrLoadModule('/src/stores/auth.js');
const { useFavoritesStore } = await server.ssrLoadModule('/src/stores/favorites.js');

function setup() {
  setActivePinia(createPinia());
  const auth = useAuthStore();
  auth.profile = { id: 'account-a' };
  return { auth, favorites: useFavoritesStore() };
}

test('toggling during initial load preserves the full list and removes an existing heart', async () => {
  const { auth, favorites } = setup();
  let resolveList;
  const calls = [];
  auth.api = (path, options = {}) => {
    calls.push([path, options.method || 'GET']);
    return options.method ? Promise.resolve(null) : new Promise(resolve => { resolveList = resolve; });
  };
  const loading = favorites.load();
  const toggling = favorites.toggle('jazz');
  resolveList(['city', 'jazz']);
  await loading;
  await toggling;
  assert.deepEqual(favorites.ids, ['city']);
  assert.deepEqual(calls, [['/favorites', 'GET'], ['/favorites/jazz', 'DELETE']]);
});

test('failed heart mutation preserves the saved list and allows retry', async () => {
  const { auth, favorites } = setup();
  auth.api = () => Promise.resolve(['jazz']);
  await favorites.load();
  auth.api = () => Promise.reject(new Error('offline'));
  await assert.rejects(favorites.toggle('jazz'), /offline/);
  assert.deepEqual(favorites.ids, ['jazz']);
  assert.deepEqual(favorites.pending, []);
  auth.api = () => Promise.resolve(null);
  await favorites.toggle('jazz');
  assert.deepEqual(favorites.ids, []);
});

test('an old account response cannot populate a new account favorites', async () => {
  const { auth, favorites } = setup();
  let resolveList;
  auth.api = () => new Promise(resolve => { resolveList = resolve; });
  const loading = favorites.load();
  auth.profile = { id: 'account-b' };
  resolveList(['city']);
  await loading;
  assert.deepEqual(favorites.ids, []);
});
