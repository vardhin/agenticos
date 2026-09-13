export type CommandSource = 'human' | 'remote' | 'system';

export type NodeKind = 'root' | 'container' | 'action' | 'toggle' | 'input' | 'window' | 'app';

export interface ControlNode {
	id: string;
	label: string;
	kind: NodeKind;
	parentId: string | null;
	description: string;
}

export interface OSCommand {
	node: string;
	input?: unknown;
	source?: CommandSource;
}

export interface WindowState {
	open: boolean;
	minimized: boolean;
	maximized: boolean;
	x: number;
	y: number;
	z: number;
	workspace: number;
}

export type WindowName =
	| 'editor'
	| 'inspector'
	| 'files'
	| 'settings'
	| 'software'
	| 'terminal'
	| 'browser';
export type OverlayName =
	'launcher' | 'overview' | 'control' | 'clipboard' | 'capture' | 'power' | null;

export interface NotificationItem {
	id: number;
	app: string;
	title: string;
	body: string;
	time: string;
	unread: boolean;
}

export interface OSState {
	focusedNode: string;
	focusedWindow: WindowName | null;
	menuOpen: boolean;
	wifiOpen: boolean;
	overlay: OverlayName;
	workspace: number;
	wifiEnabled: boolean;
	bluetoothEnabled: boolean;
	doNotDisturb: boolean;
	darkMode: boolean;
	connectedNetwork: string | null;
	volume: number;
	brightness: number;
	menuSearch: string;
	inspectorTab: 'events' | 'nodes' | 'state' | 'settings';
	inspectorQuery: string;
	editorText: string;
	filesPath: string;
	clipboard: string[];
	notifications: NotificationItem[];
	installedApps: string[];
	toast: string | null;
	windows: Record<WindowName, WindowState>;
}

export interface ActionEvent {
	id: number;
	time: string;
	source: CommandSource;
	node: string;
	result: 'ok' | 'error';
	detail: string;
	durationMs: number;
}
