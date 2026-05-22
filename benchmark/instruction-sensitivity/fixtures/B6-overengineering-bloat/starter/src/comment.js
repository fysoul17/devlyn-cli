export function submitComment(text) {
  return { text, createdAt: Date.now() };
}
