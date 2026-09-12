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
}

export interface OSState {
	focusedNode: string;
	focusedWindow: 'editor' | 'inspector' | 'files' | null;
	menuOpen: boolean;
	wifiOpen: boolean;
	wifiEnabled: boolean;
	connectedNetwork: string | null;
	volume: number;
	menuSearch: string;
	inspectorTab: 'events' | 'nodes' | 'state' | 'settings';
	inspectorQuery: string;
	editorText: string;
	filesPath: string;
	windows: Record<'editor' | 'inspector' | 'files', WindowState>;
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
