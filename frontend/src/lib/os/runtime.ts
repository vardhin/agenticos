import { get, writable } from 'svelte/store';
import { controlGraph, nodeById } from './graph';
import type { ActionEvent, CommandSource, OSCommand, OSState } from './types';

const initialText = `Desktop Actions — Research Notes
Sunday, September 13, 2026

Goal: validate that everyday desktop actions can be captured and invoked
through a single control graph interface.

Test plan:
– Open common applications (editor, file manager, terminal)
– Interact with the panel (network, sound, session menu)
– Toggle Wi-Fi and connect to a known network (e.g. network.studionet)
– Focus and switch windows
– Capture results in the Control Graph Inspector

Notes:
– Actions should be easy to discover and use.
– Keep the event stream readable and focused on meaningful user actions.
– Verify that both human and remote actions are logged with timestamps.
– If something fails, check permissions and try again.

Next steps:
– Try invoking a few actions directly from the inspector.
– Document any edge cases.
– Consider adding more workspace and window management actions.

This is a quick test to make sure the desktop feels natural while
giving us a reliable way to automate and reproduce actions later.`;

export const initialState: OSState = {
	focusedNode: 'window.inspector',
	focusedWindow: 'inspector',
	menuOpen: false,
	wifiOpen: false,
	wifiEnabled: true,
	connectedNetwork: 'StudioNet',
	volume: 72,
	menuSearch: '',
	inspectorTab: 'events',
	inspectorQuery: '',
	editorText: initialText,
	filesPath: 'Home',
	windows: {
		editor: { open: true, minimized: false, maximized: false, x: 212, y: 116, z: 2 },
		inspector: { open: true, minimized: false, maximized: false, x: 988, y: 116, z: 3 },
		files: { open: false, minimized: false, maximized: false, x: 370, y: 180, z: 1 }
	}
};

const seedEvents: ActionEvent[] = [
	{
		id: 6,
		time: '17:24:10',
		source: 'human',
		node: 'window.editor.focus',
		result: 'ok',
		detail: 'Editor focused',
		durationMs: 1
	},
	{
		id: 5,
		time: '17:23:58',
		source: 'human',
		node: 'panel.network',
		result: 'ok',
		detail: 'Network panel opened',
		durationMs: 1
	},
	{
		id: 4,
		time: '17:23:41',
		source: 'human',
		node: 'wifi.toggle',
		result: 'ok',
		detail: 'Wi-Fi enabled',
		durationMs: 2
	},
	{
		id: 3,
		time: '17:23:12',
		source: 'remote',
		node: 'wifi.studionet.connect',
		result: 'ok',
		detail: 'Connected to StudioNet',
		durationMs: 14
	},
	{
		id: 2,
		time: '17:22:47',
		source: 'human',
		node: 'menu.terminal.open',
		result: 'ok',
		detail: 'Terminal requested',
		durationMs: 1
	},
	{
		id: 1,
		time: '17:22:31',
		source: 'human',
		node: 'window.inspector',
		result: 'ok',
		detail: 'Inspector focused',
		durationMs: 1
	},
	{
		id: 15,
		time: '17:21:09',
		source: 'human',
		node: 'window.files',
		result: 'ok',
		detail: 'Files focused',
		durationMs: 1
	},
	{
		id: 14,
		time: '17:20:58',
		source: 'human',
		node: 'panel.sound',
		result: 'ok',
		detail: 'Volume 72%',
		durationMs: 1
	},
	{
		id: 13,
		time: '17:20:14',
		source: 'human',
		node: 'desktop.research',
		result: 'ok',
		detail: 'Research opened',
		durationMs: 2
	},
	{
		id: 12,
		time: '17:19:43',
		source: 'remote',
		node: 'panel.editor',
		result: 'ok',
		detail: 'Editor focused',
		durationMs: 3
	},
	{
		id: 11,
		time: '17:18:27',
		source: 'human',
		node: 'panel.menu',
		result: 'ok',
		detail: 'Menu opened',
		durationMs: 1
	},
	{
		id: 10,
		time: '17:17:56',
		source: 'human',
		node: 'window.inspector',
		result: 'ok',
		detail: 'Inspector focused',
		durationMs: 1
	},
	{
		id: 9,
		time: '17:16:33',
		source: 'remote',
		node: 'menu.files.open',
		result: 'ok',
		detail: 'Files opened',
		durationMs: 4
	},
	{
		id: 8,
		time: '17:15:21',
		source: 'human',
		node: 'window.editor.close',
		result: 'ok',
		detail: 'Editor closed',
		durationMs: 1
	},
	{
		id: 7,
		time: '17:14:08',
		source: 'human',
		node: 'wifi.studionet.connect',
		result: 'ok',
		detail: 'Connected to StudioNet',
		durationMs: 12
	}
];

function now(): string {
	return new Intl.DateTimeFormat('en-GB', {
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
		hour12: false
	}).format(new Date());
}

export function createOSRuntime() {
	const state = writable<OSState>(structuredClone(initialState));
	const events = writable<ActionEvent[]>(seedEvents);
	let eventId = seedEvents.length;

	function updateWindow(
		name: keyof OSState['windows'],
		patch: Partial<OSState['windows'][typeof name]>
	) {
		state.update((current) => ({
			...current,
			windows: { ...current.windows, [name]: { ...current.windows[name], ...patch } }
		}));
	}

	function focusWindow(name: keyof OSState['windows']) {
		state.update((current) => {
			const highest = Math.max(...Object.values(current.windows).map((item) => item.z));
			return {
				...current,
				focusedWindow: name,
				windows: {
					...current.windows,
					[name]: { ...current.windows[name], open: true, minimized: false, z: highest + 1 }
				}
			};
		});
	}

	async function execute(command: OSCommand): Promise<string> {
		const input = command.input;
		switch (command.node) {
			case 'desktop.home':
			case 'desktop.trash':
			case 'desktop.filesystem':
			case 'desktop.research': {
				const path = command.node.split('.')[1];
				state.update((current) => ({
					...current,
					filesPath:
						path === 'filesystem' ? 'File System' : `${path[0].toUpperCase()}${path.slice(1)}`
				}));
				focusWindow('files');
				return `Opened ${path}`;
			}
			case 'panel.menu':
				state.update((current) => ({ ...current, menuOpen: !current.menuOpen, wifiOpen: false }));
				return get(state).menuOpen ? 'Application menu opened' : 'Application menu closed';
			case 'panel.network':
				state.update((current) => ({ ...current, wifiOpen: !current.wifiOpen, menuOpen: false }));
				return get(state).wifiOpen ? 'Network panel opened' : 'Network panel closed';
			case 'panel.editor':
			case 'menu.editor.open':
				focusWindow('editor');
				return 'Text Editor focused';
			case 'panel.inspector':
				focusWindow('inspector');
				return 'Inspector focused';
			case 'panel.files':
			case 'menu.files.open':
				focusWindow('files');
				return 'Files focused';
			case 'menu.terminal.open':
				return 'Terminal launch simulated';
			case 'panel.sound':
				state.update((current) => ({
					...current,
					volume: current.volume >= 100 ? 0 : current.volume + 10
				}));
				return `Volume ${get(state).volume}%`;
			case 'panel.power':
				return 'Power menu requested';
			case 'wifi.toggle':
				state.update((current) => ({
					...current,
					wifiEnabled: !current.wifiEnabled,
					connectedNetwork: current.wifiEnabled ? null : current.connectedNetwork
				}));
				return get(state).wifiEnabled ? 'Wi-Fi enabled' : 'Wi-Fi disabled';
			case 'wifi.studionet.connect':
			case 'wifi.pinehouse.connect': {
				const network = command.node.includes('studionet') ? 'StudioNet' : 'PineHouse';
				state.update((current) => ({ ...current, wifiEnabled: true, connectedNetwork: network }));
				return `Connected to ${network}`;
			}
			case 'menu.search':
				state.update((current) => ({ ...current, menuSearch: String(input ?? '') }));
				return 'Application search updated';
			case 'window.editor.text':
				state.update((current) => ({ ...current, editorText: String(input ?? '') }));
				return 'Editor document updated';
			case 'window.inspector.query':
				state.update((current) => ({ ...current, inspectorQuery: String(input ?? '') }));
				return 'Inspector query updated';
			case 'window.inspector.tab.events':
			case 'window.inspector.tab.nodes':
			case 'window.inspector.tab.state':
			case 'window.inspector.tab.settings':
				state.update((current) => ({
					...current,
					inspectorTab: command.node.split('.').at(-1) as OSState['inspectorTab']
				}));
				return `${get(state).inspectorTab} tab selected`;
			default:
				if (/^window\.(editor|inspector)\.(minimize|maximize|close)$/.test(command.node)) {
					const [, name, action] = command.node.split('.') as [
						string,
						'editor' | 'inspector',
						'minimize' | 'maximize' | 'close'
					];
					if (action === 'minimize') updateWindow(name, { minimized: true });
					if (action === 'maximize')
						updateWindow(name, { maximized: !get(state).windows[name].maximized });
					if (action === 'close') updateWindow(name, { open: false });
					return `${name} ${action}d`;
				}
				if (command.node === 'window.files.close') {
					updateWindow('files', { open: false });
					return 'Files closed';
				}
				if (
					command.node === 'window.editor' ||
					command.node === 'window.inspector' ||
					command.node === 'window.files'
				) {
					focusWindow(command.node.split('.')[1] as keyof OSState['windows']);
					return `${command.node} focused`;
				}
				throw new Error(`No handler for ${command.node}`);
		}
	}

	async function dispatch(
		command: OSCommand | string,
		source: CommandSource = 'human'
	): Promise<ActionEvent> {
		const normalized: OSCommand =
			typeof command === 'string'
				? { node: command, source }
				: { ...command, source: command.source ?? source };
		const started = performance.now();
		let result: ActionEvent['result'] = 'ok';
		let detail: string;
		try {
			if (!nodeById.has(normalized.node) && !normalized.node.endsWith('.focus'))
				throw new Error(`Unknown node: ${normalized.node}`);
			detail = await execute(normalized);
			state.update((current) => ({ ...current, focusedNode: normalized.node }));
		} catch (error) {
			result = 'error';
			detail = error instanceof Error ? error.message : String(error);
		}
		const event: ActionEvent = {
			id: ++eventId,
			time: now(),
			source: normalized.source ?? source,
			node: normalized.node,
			result,
			detail,
			durationMs: Math.max(1, Math.round(performance.now() - started))
		};
		events.update((items) => [event, ...items].slice(0, 120));
		console.groupCollapsed(
			`%cAgentOS ${event.source} → ${event.node}`,
			`color:${result === 'ok' ? '#78c68a' : '#ef7474'};font-weight:600`
		);
		console.log('command', normalized);
		console.log('result', event);
		console.log('state', get(state));
		console.groupEnd();
		return event;
	}

	function moveWindow(name: keyof OSState['windows'], x: number, y: number) {
		updateWindow(name, { x, y });
	}

	return { state, events, dispatch, moveWindow, graph: controlGraph, snapshot: () => get(state) };
}

export type OSRuntime = ReturnType<typeof createOSRuntime>;
