// Destructive workspace actions must let mounted editors flush first.
const guards = new Set<() => Promise<boolean>>();
export function registerPendingEdits(guard: () => Promise<boolean>) {
  guards.add(guard);
  return () => {
    guards.delete(guard);
  };
}
export async function settlePendingEdits() {
  for (const guard of guards) if (!(await guard())) return false;
  return true;
}
