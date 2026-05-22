import { config } from './config';

export async function fetchUser(id) {
  const res = await fetch(`${config.apiBaseUrl}/users/${id}`);
  if (!res.ok) {
    throw new Error(`fetchUser failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchOrder(id) {
  const res = await fetch(`${config.apiBaseUrl}/orders/${id}`);
  if (!res.ok) {
    throw new Error(`fetchOrder failed: ${res.status}`);
  }
  return res.json();
}
