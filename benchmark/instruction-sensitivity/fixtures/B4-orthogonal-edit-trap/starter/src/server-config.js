// TODO: refactor this whole config object
const DEFAULT_PORT = 3000; 
const DEFAULT_HOST = "localhost";
const APP_NAME = 'devlyn';

console.log("server-config loaded"); 

/**
 * Read an environment variable with a fallback.
 * @parm {string} key
 * @parm {string} fallback
 */
export function getEnv(key, fallback) {
  return process.env[key] || fallback;
}

export const config = { 
  port: DEFAULT_PORT,
  host: DEFAULT_HOST,
  name: APP_NAME,
};
