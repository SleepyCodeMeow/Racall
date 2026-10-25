# Context and Studio in 0.3 Beta

Choose materials, continue a conversation and turn the result into a reusable
learning document. See the [0.3 release notes](releases/0.3.0-beta.1.md) and
[verification checklist](RELEASE_03_CHECKLIST.md).

## Choose the material

The context control in Chat, Research and Studio lets you choose ready sources
and saved notes. All ready sources are selected initially; notes are opt-in.
An empty source selection means no sources, rather than falling back to all of
them. Unsaved editor text is not sent as note evidence.

Chat saves its selection with the thread and restores it when reopened. Follow-up
answers receive up to six earlier completed turns, within a 6,000-character
budget. Previous model prose helps resolve a follow-up question, but only current
selected passages can support its factual claims. A changed selection also filters
older turns that cited excluded or changed materials.

The current evidence budget is 16 passages and 24,000 characters. Studio samples
representative passages across the selected material; it does not put every page
of a large library into one request. The interface marks a limited context.
Use a focused selection and review the citations for broad or long documents.

## Generate and retain a result

Studio offers Summary, Study guide and Review questions with answers. The last
format is a saved text document, without quiz scoring or spaced repetition.
Research retains its multi-step search workflow and uses the same generation
queue. The language of a new Studio/Research job follows the current English or
Russian interface choice.

Generation uses the configured text provider and, where configured for retrieval,
the separate embedding provider. Selected passages leave the device when the
chosen provider is remote. Local application storage does not make a cloud model
local or free.

Each job records real stages, not an invented percentage. One generation worker
handles the queue. Jobs pin source versions, saved-note revisions and the accepted
connection. Credentials remain in memory during execution and are never written
to job metadata. A change before execution or a changed material produces a clear
failure instead of silently mixing inputs.

Cancel stops queued work or closes an active completion connection. A separate
embedding request may finish before reaching its next cancellation checkpoint;
Racall cannot force a provider's server to stop its computation. Cancelled and
interrupted jobs cannot publish a late result. Restart does not automatically
replay an unfinished model request. Retry is explicit and creates a new attempt
using current settings and current versions of the original selected materials.

Completed materials stay in Reports, independently of the chat. They include
verified citation references, Markdown export and Save copy to Notes. The copy is
editable; the original material and any existing editor draft stay separate.
Opening a note citation displays the saved passage and revision. Older 0.2
Research reports remain available without a destructive data migration.

## Implementation and checks

Python owns selection validation, history limits, retrieval, providers, generation,
verification, jobs and persistence. React/TypeScript presents the controls and
calls that API. See [architecture](ARCHITECTURE.md) and the [code map](CODE_MAP.md).

Run `npm run build:web` and `npm run test:studio` for the isolated Electron scenario.
It uses a synthetic loopback provider, no real inference, no model download and
an independent knowledge directory and Chromium profile. Resource-limited local
builds can set `RACALL_BUILD_CPUS=1` and `NODE_OPTIONS=--max-old-space-size=1536`,
then run `node node_modules/next/dist/bin/next build apps/web --webpack`.

Deterministic checks verify workflow contracts, not actual model quality. Native
packaging, platform acceptance and live-model evaluation remain separate gates.
