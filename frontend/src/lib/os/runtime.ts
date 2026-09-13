import { get, writable } from 'svelte/store';
import { controlGraph, nodeById } from './graph';
import { osApi } from './api';
import type {
	ActionEvent,
	CommandSource,
	OSCommand,
	OSState,
	OverlayName,
	WindowName
} from './types';

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
	overlay: null,
	workspace: 1,
	wifiEnabled: true,
	bluetoothEnabled: true,
	doNotDisturb: false,
	darkMode: true,
	connectedNetwork: 'StudioNet',
	volume: 72,
	brightness: 84,
	menuSearch: '',
	inspectorTab: 'events',
	inspectorQuery: '',
	editorText: initialText,
	filesPath: 'Home',
	clipboard: ['https://agentos.dev/docs', 'Desktop Actions — Research Notes', 'pacman -Syu'],
	notifications: [
		{
			id: 1,
			app: 'Software',
			title: 'Updates are ready',
			body: '3 application updates can be installed.',
			time: '2 min',
			unread: true
		},
		{
			id: 2,
			app: 'Files',
			title: 'Archive extracted',
			body: 'research-assets.zip was extracted to Downloads.',
			time: '18 min',
			unread: true
		},
		{
			id: 3,
			app: 'System',
			title: 'Welcome to AgentOS',
			body: 'Press Super to search apps, files and settings.',
			time: 'Today',
			unread: false
		}
	],
	installedApps: ['Browser', 'Files', 'Text Editor', 'Terminal', 'Settings'],
	toast: null,
	windows: {
		editor: { open: true, minimized: false, maximized: false, x: 212, y: 116, z: 2, workspace: 1 },
		inspector: {
			open: true,
			minimized: false,
			maximized: false,
			x: 988,
			y: 116,
			z: 3,
			workspace: 1
		},
		files: { open: false, minimized: false, maximized: false, x: 370, y: 180, z: 1, workspace: 1 },
		settings: {
			open: false,
			minimized: false,
			maximized: false,
			x: 420,
			y: 145,
			z: 1,
			workspace: 1
		},
		software: {
			open: false,
			minimized: false,
			maximized: false,
			x: 470,
			y: 135,
			z: 1,
			workspace: 1
		},
		terminal: {
			open: false,
			minimized: false,
			maximized: false,
			x: 330,
			y: 210,
			z: 1,
			workspace: 1
		},
		browser: {
			open: false,
			minimized: false,
			maximized: false,
			x: 280,
			y: 130,
			z: 1,
			workspace: 1
		}
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
	let persistState = false;
	let persistTimer: ReturnType<typeof setTimeout> | undefined;
	const externalHandlers = new Map<string, (input: unknown) => Promise<string> | string>();

	async function initialize() {
		try {
			const [savedState, savedEvents] = await Promise.all([osApi.loadState(), osApi.loadEvents()]);
			if (Object.keys(savedState).length > 0) {
				state.set({
					...structuredClone(initialState),
					...savedState,
					windows: { ...structuredClone(initialState.windows), ...savedState.windows },
					toast: null,
					overlay: null,
					menuOpen: false,
					wifiOpen: false
				});
			}
			if (savedEvents.length > 0) {
				events.set(savedEvents);
				eventId = Math.max(...savedEvents.map((event) => event.id));
			}
			persistState = true;
			if (Object.keys(savedState).length === 0) await osApi.saveState(get(state));
			return true;
		} catch {
			// The desktop remains fully usable in-memory when its optional API is offline.
			return false;
		}
	}

	state.subscribe((value) => {
		if (!persistState) return;
		if (persistTimer) clearTimeout(persistTimer);
		persistTimer = setTimeout(() => void osApi.saveState(value).catch(() => undefined), 250);
	});

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
			const targetWorkspace = current.windows[name].open
				? current.windows[name].workspace
				: current.workspace;
			return {
				...current,
				focusedWindow: name,
				workspace: targetWorkspace,
				windows: {
					...current.windows,
					[name]: {
						...current.windows[name],
						open: true,
						minimized: false,
						workspace: targetWorkspace,
						z: highest + 1
					}
				}
			};
		});
	}

	function showOverlay(overlay: OverlayName) {
		state.update((current) => ({
			...current,
			overlay: current.overlay === overlay ? null : overlay,
			menuOpen: false,
			wifiOpen: false
		}));
	}

	function toast(message: string) {
		state.update((current) => ({ ...current, toast: message }));
		setTimeout(
			() =>
				state.update((current) =>
					current.toast === message ? { ...current, toast: null } : current
				),
			2400
		);
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
				showOverlay('launcher');
				return get(state).overlay === 'launcher' ? 'Launcher opened' : 'Launcher closed';
			case 'panel.overview':
				showOverlay('overview');
				return 'Workspace overview toggled';
			case 'panel.control':
				showOverlay('control');
				return 'Control Centre toggled';
			case 'panel.clipboard':
				showOverlay('clipboard');
				return 'Clipboard history toggled';
			case 'panel.capture':
				showOverlay('capture');
				return 'Screen capture opened';
			case 'panel.network':
				state.update((current) => ({
					...current,
					wifiOpen: !current.wifiOpen,
					menuOpen: false,
					overlay: null
				}));
				return get(state).wifiOpen ? 'Network panel opened' : 'Network panel closed';
			case 'panel.editor':
			case 'menu.editor.open':
				focusWindow('editor');
				state.update((current) => ({ ...current, overlay: null, menuOpen: false }));
				return 'Text Editor focused';
			case 'panel.inspector':
				focusWindow('inspector');
				state.update((current) => ({ ...current, overlay: null, menuOpen: false }));
				return 'Inspector focused';
			case 'panel.files':
			case 'menu.files.open':
				focusWindow('files');
				state.update((current) => ({ ...current, overlay: null, menuOpen: false }));
				return 'Files focused';
			case 'menu.terminal.open':
				focusWindow('terminal');
				state.update((current) => ({ ...current, overlay: null }));
				return 'Terminal opened';
			case 'menu.settings.open':
				focusWindow('settings');
				state.update((current) => ({ ...current, overlay: null }));
				return 'Settings opened';
			case 'menu.software.open':
				focusWindow('software');
				state.update((current) => ({ ...current, overlay: null }));
				return 'Software opened';
			case 'menu.browser.open':
				focusWindow('browser');
				state.update((current) => ({ ...current, overlay: null }));
				return 'Browser opened';
			case 'panel.sound':
				state.update((current) => ({
					...current,
					volume: current.volume >= 100 ? 0 : current.volume + 10
				}));
				return `Volume ${get(state).volume}%`;
			case 'panel.power':
				showOverlay('power');
				return 'Power menu opened';
			case 'control.bluetooth.toggle':
				state.update((current) => ({ ...current, bluetoothEnabled: !current.bluetoothEnabled }));
				return `Bluetooth ${get(state).bluetoothEnabled ? 'enabled' : 'disabled'}`;
			case 'control.dnd.toggle':
				state.update((current) => ({ ...current, doNotDisturb: !current.doNotDisturb }));
				return `Do Not Disturb ${get(state).doNotDisturb ? 'enabled' : 'disabled'}`;
			case 'control.theme.toggle':
				state.update((current) => ({ ...current, darkMode: !current.darkMode }));
				return `${get(state).darkMode ? 'Dark' : 'Light'} appearance selected`;
			case 'control.volume':
				state.update((current) => ({
					...current,
					volume: Math.max(0, Math.min(100, Number(input)))
				}));
				return `Volume ${get(state).volume}%`;
			case 'control.brightness':
				state.update((current) => ({
					...current,
					brightness: Math.max(10, Math.min(100, Number(input)))
				}));
				return `Brightness ${get(state).brightness}%`;
			case 'notifications.clear':
				state.update((current) => ({ ...current, notifications: [] }));
				return 'Notifications cleared';
			case 'notifications.dismiss':
				state.update((current) => ({
					...current,
					notifications: current.notifications.filter((item) => item.id !== Number(input))
				}));
				return 'Notification dismissed';
			case 'workspace.switch': {
				const workspace = Math.max(1, Math.min(4, Number(input)));
				state.update((current) => ({ ...current, workspace, overlay: null }));
				return `Switched to workspace ${workspace}`;
			}
			case 'workspace.window.move': {
				const value = input as { window: WindowName; workspace: number };
				updateWindow(value.window, { workspace: value.workspace });
				return `Moved ${value.window} to workspace ${value.workspace}`;
			}
			case 'clipboard.copy': {
				const value = String(input ?? '');
				state.update((current) => ({
					...current,
					clipboard: [value, ...current.clipboard.filter((item) => item !== value)].slice(0, 8)
				}));
				toast('Copied to clipboard');
				return 'Clipboard item copied';
			}
			case 'capture.save':
				state.update((current) => ({ ...current, overlay: null }));
				toast(`${String(input ?? 'Screenshot')} saved to Pictures`);
				return 'Capture saved';
			case 'software.toggle': {
				const app = String(input);
				state.update((current) => ({
					...current,
					installedApps: current.installedApps.includes(app)
						? current.installedApps.filter((item) => item !== app)
						: [...current.installedApps, app]
				}));
				return `${app} ${get(state).installedApps.includes(app) ? 'installed' : 'removed'}`;
			}
			case 'files.path':
				state.update((current) => ({ ...current, filesPath: String(input) }));
				return `Opened ${String(input)}`;
			case 'files.action':
				toast(String(input));
				return String(input);
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
				if (externalHandlers.has(command.node))
					return await externalHandlers.get(command.node)!(command.input);
				if (
					/^window\.(editor|inspector|files|settings|software|terminal|browser)\.(minimize|maximize|close)$/.test(
						command.node
					)
				) {
					const [, name, action] = command.node.split('.') as [
						string,
						WindowName,
						'minimize' | 'maximize' | 'close'
					];
					if (action === 'minimize') updateWindow(name, { minimized: true });
					if (action === 'maximize')
						updateWindow(name, { maximized: !get(state).windows[name].maximized });
					if (action === 'close') updateWindow(name, { open: false });
					return `${name} ${action}d`;
				}
				if (/^window\.(editor|inspector|files|settings|software|terminal|browser)$/.test(command.node)) {
					focusWindow(command.node.split('.')[1] as WindowName);
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
		if (persistState) void osApi.logEvent(event, normalized.input).catch(() => undefined);
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

	// High-frequency text editing should update the shared state without creating
	// one control-graph event per keystroke. Explicit agent-driven text changes
	// still go through window.editor.text and remain observable.
	function setEditorText(editorText: string) {
		state.update((current) => ({ ...current, editorText }));
	}

	function registerHandler(node: string, handler: (input: unknown) => Promise<string> | string) {
		externalHandlers.set(node, handler);
		return () => externalHandlers.delete(node);
	}

	return {
		state,
		events,
		dispatch,
		moveWindow,
		setEditorText,
		registerHandler,
		initialize,
		graph: controlGraph,
		snapshot: () => get(state)
	};
}

export type OSRuntime = ReturnType<typeof createOSRuntime>;
