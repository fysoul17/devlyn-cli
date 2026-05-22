import { config } from '../config';

// Thin wrapper over the Redis client. Network-backed, shared across instances.
let client = null;

function getClient() {
  if (!client) {
    client = createRedisClient(config.redisUrl);
  }
  return client;
}

export async function redisFetch(key) {
  const raw = await getClient().get(key);
  return raw ? JSON.parse(raw) : undefined;
}

export async function redisStore(key, value, { expirySeconds }) {
  await getClient().set(key, JSON.stringify(value), 'EX', expirySeconds);
}
