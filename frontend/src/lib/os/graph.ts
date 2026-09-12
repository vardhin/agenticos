import type { ControlNode } from './types';

export const controlGraph: ControlNode[] = [
	{
		id: 'desktop',
		label: 'Desktop',
		kind: 'root',
		parentId: null,
		description: 'Desktop root surface'
	},
	{
		id: 'desktop.home',
		label: 'Home',
		kind: 'action',
		parentId: 'desktop',
		description: 'Open the home directory'
	},
	{
		id: 'desktop.trash',
		label: 'Trash',
		kind: 'action',
		parentId: 'desktop',
		description: 'Open the trash directory'
	},
	{
		id: 'desktop.filesystem',
		label: 'File System',
		kind: 'action',
		parentId: 'desktop',
		description: 'Open the root filesystem'
	},
	{
		id: 'desktop.research',
		label: 'Research',
		kind: 'action',
		parentId: 'desktop',
		description: 'Open the research directory'
	},
	{
		id: 'panel',
		label: 'Panel',
		kind: 'container',
		parentId: 'desktop',
		description: 'Bottom system panel'
	},
	{
		id: 'panel.menu',
		label: 'Applications',
		kind: 'toggle',
		parentId: 'panel',
		description: 'Toggle the application menu'
	},
	{
		id: 'panel.editor',
		label: 'Text Editor',
		kind: 'app',
		parentId: 'panel',
		description: 'Show or focus the text editor'
	},
	{
		id: 'panel.inspector',
		label: 'Control Graph Inspector',
		kind: 'app',
		parentId: 'panel',
		description: 'Show or focus the graph inspector'
	},
	{
		id: 'panel.files',
		label: 'Files',
		kind: 'app',
		parentId: 'panel',
		description: 'Show or focus the file manager'
	},
	{
		id: 'panel.network',
		label: 'Network',
		kind: 'toggle',
		parentId: 'panel',
		description: 'Toggle the network panel'
	},
	{
		id: 'panel.sound',
		label: 'Sound',
		kind: 'action',
		parentId: 'panel',
		description: 'Cycle the output volume'
	},
	{
		id: 'panel.power',
		label: 'Power',
		kind: 'action',
		parentId: 'panel',
		description: 'Record a power-menu request'
	},
	{
		id: 'menu',
		label: 'Application menu',
		kind: 'container',
		parentId: 'panel.menu',
		description: 'Application launcher'
	},
	{
		id: 'menu.search',
		label: 'Search applications',
		kind: 'input',
		parentId: 'menu',
		description: 'Update application search text'
	},
	{
		id: 'menu.editor.open',
		label: 'Open Text Editor',
		kind: 'action',
		parentId: 'menu',
		description: 'Launch the text editor'
	},
	{
		id: 'menu.files.open',
		label: 'Open Files',
		kind: 'action',
		parentId: 'menu',
		description: 'Launch the file manager'
	},
	{
		id: 'menu.terminal.open',
		label: 'Open Terminal',
		kind: 'action',
		parentId: 'menu',
		description: 'Launch a simulated terminal'
	},
	{
		id: 'wifi',
		label: 'Wi-Fi',
		kind: 'container',
		parentId: 'panel.network',
		description: 'Wireless network controls'
	},
	{
		id: 'wifi.toggle',
		label: 'Wi-Fi enabled',
		kind: 'toggle',
		parentId: 'wifi',
		description: 'Enable or disable Wi-Fi'
	},
	{
		id: 'wifi.studionet.connect',
		label: 'StudioNet',
		kind: 'action',
		parentId: 'wifi',
		description: 'Connect to StudioNet'
	},
	{
		id: 'wifi.pinehouse.connect',
		label: 'PineHouse',
		kind: 'action',
		parentId: 'wifi',
		description: 'Connect to PineHouse'
	},
	{
		id: 'window.editor',
		label: 'Text Editor window',
		kind: 'window',
		parentId: 'desktop',
		description: 'Editable research notes'
	},
	{
		id: 'window.editor.text',
		label: 'Editor document',
		kind: 'input',
		parentId: 'window.editor',
		description: 'Update editor text'
	},
	{
		id: 'window.editor.minimize',
		label: 'Minimize editor',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Minimize editor window'
	},
	{
		id: 'window.editor.maximize',
		label: 'Maximize editor',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Toggle editor maximization'
	},
	{
		id: 'window.editor.close',
		label: 'Close editor',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Close editor window'
	},
	{
		id: 'window.inspector',
		label: 'Control Graph Inspector',
		kind: 'window',
		parentId: 'desktop',
		description: 'Inspect nodes, events and state'
	},
	{
		id: 'window.inspector.tab.events',
		label: 'Events tab',
		kind: 'action',
		parentId: 'window.inspector',
		description: 'Show action events'
	},
	{
		id: 'window.inspector.tab.nodes',
		label: 'Nodes tab',
		kind: 'action',
		parentId: 'window.inspector',
		description: 'Show registered graph nodes'
	},
	{
		id: 'window.inspector.tab.state',
		label: 'State tab',
		kind: 'action',
		parentId: 'window.inspector',
		description: 'Show current environment state'
	},
	{
		id: 'window.inspector.tab.settings',
		label: 'Settings tab',
		kind: 'action',
		parentId: 'window.inspector',
		description: 'Show inspector settings'
	},
	{
		id: 'window.inspector.query',
		label: 'Inspector filter',
		kind: 'input',
		parentId: 'window.inspector',
		description: 'Filter inspector content'
	},
	{
		id: 'window.inspector.minimize',
		label: 'Minimize inspector',
		kind: 'action',
		parentId: 'window.inspector',
		description: 'Minimize inspector window'
	},
	{
		id: 'window.inspector.maximize',
		label: 'Maximize inspector',
		kind: 'action',
		parentId: 'window.inspector',
		description: 'Toggle inspector maximization'
	},
	{
		id: 'window.inspector.close',
		label: 'Close inspector',
		kind: 'action',
		parentId: 'window.inspector',
		description: 'Close inspector window'
	},
	{
		id: 'window.files',
		label: 'Files window',
		kind: 'window',
		parentId: 'desktop',
		description: 'Browse simulated directories'
	},
	{
		id: 'window.files.close',
		label: 'Close Files',
		kind: 'action',
		parentId: 'window.files',
		description: 'Close Files window'
	}
];

export const nodeById = new Map(controlGraph.map((node) => [node.id, node]));

export function childrenOf(parentId: string): ControlNode[] {
	return controlGraph.filter((node) => node.parentId === parentId);
}
