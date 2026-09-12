# AgentOS research desktop

A functional SvelteKit desktop simulation backed by a semantic control graph. Human interactions and remote commands use the same async dispatcher and emit the same inspectable events.

## Run

```sh
bun run dev
```

## Invoke nodes

From the in-desktop Control Graph Inspector, enter a node ID such as `panel.network`, `wifi.toggle`, or `desktop.research`.

From another process, send any action to the single control endpoint:

```sh
curl -X POST http://127.0.0.1:5173/api/control \
  -H 'content-type: application/json' \
  -d '{"node":"panel.network"}'
```

Input nodes accept a payload:

```sh
curl -X POST http://127.0.0.1:5173/api/control \
  -H 'content-type: application/json' \
  -d '{"node":"menu.search","input":"Files"}'
```

The browser also exposes `window.agentOS.dispatch()`, listens for `agentos:command` custom events and `postMessage` commands, and receives server commands over one EventSource connection. Use the Inspector's Events, Nodes, and State tabs—or the browser console—to observe every transition.

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```sh
# create a new project
npx sv create my-app
```

To recreate this project with the same configuration:

```sh
# recreate this project
bun x sv@0.17.0 create --template minimal --types ts --add prettier eslint playwright tailwindcss="plugins:typography,forms" mdsvex ai-tools="ide:vscode,other+tools:mcp,svelte-code-writer,svelte-core-bestpractices,svelte-file-editor+mcpSetup:local" --install bun ./
```

## Developing

Once you've created a project and installed dependencies with `npm install` (or `pnpm install` or `yarn`), start a development server:

```sh
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

## Building

To create a production version of your app:

```sh
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.
