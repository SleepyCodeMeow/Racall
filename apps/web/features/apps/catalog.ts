import integrations from '../../../shared/launchers.json';
// These are fixed Ollama integration IDs, never shell input from a model or user.
// Commands are copied for inspection and manual launch; Racall does not execute them.
export const launchers = integrations;

export function launchCommand(id: (typeof launchers)[number]['id']) {
  return `ollama launch ${id}`;
}
