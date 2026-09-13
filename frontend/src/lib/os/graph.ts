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
		id: 'window.editor.paste',
		label: 'Paste into document',
		kind: 'input',
		parentId: 'window.editor',
		description: 'Paste supplied clipboard content into the active document'
	},
	{
		id: 'window.editor.new',
		label: 'New text document',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Create a blank unsaved text document'
	},
	{
		id: 'window.editor.save',
		label: 'Save text document',
		kind: 'input',
		parentId: 'window.editor',
		description: 'Save the active document; input may provide a new filename'
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
	},
	{
		id: 'window.files.minimize',
		label: 'Minimize Files',
		kind: 'action',
		parentId: 'window.files',
		description: 'Minimize Files'
	},
	{
		id: 'window.files.maximize',
		label: 'Maximize Files',
		kind: 'action',
		parentId: 'window.files',
		description: 'Toggle Files maximization'
	},
	{
		id: 'panel.overview',
		label: 'Overview',
		kind: 'toggle',
		parentId: 'panel',
		description: 'Show windows and workspaces'
	},
	{
		id: 'panel.control',
		label: 'Control Centre',
		kind: 'toggle',
		parentId: 'panel',
		description: 'Show quick settings and notifications'
	},
	{
		id: 'panel.clipboard',
		label: 'Clipboard',
		kind: 'toggle',
		parentId: 'panel',
		description: 'Show clipboard history'
	},
	{
		id: 'panel.capture',
		label: 'Capture',
		kind: 'toggle',
		parentId: 'panel',
		description: 'Take a screenshot or recording'
	},
	{
		id: 'menu.browser.open',
		label: 'Open Browser',
		kind: 'action',
		parentId: 'menu',
		description: 'Launch the web browser'
	},
	{
		id: 'window.browser',
		label: 'Browser window',
		kind: 'window',
		parentId: 'desktop',
		description: 'Navigate the embedded web browser'
	},
	{
		id: 'window.browser.navigate',
		label: 'Navigate Browser',
		kind: 'input',
		parentId: 'window.browser',
		description: 'Navigate to a URL or search query'
	},
	{
		id: 'browser.focus',
		label: 'Focus Browser',
		kind: 'action',
		parentId: 'window.browser',
		description: 'Show and focus the browser window'
	},
	{
		id: 'browser.copy_url',
		label: 'Copy Browser Address',
		kind: 'action',
		parentId: 'window.browser',
		description: 'Copy the current browser address to the clipboard'
	},
	...['minimize', 'maximize', 'close'].map((action) => ({
		id: `window.browser.${action}`,
		label: `${action[0].toUpperCase()}${action.slice(1)} Browser`,
		kind: 'action' as const,
		parentId: 'window.browser',
		description: `${action[0].toUpperCase()}${action.slice(1)} the Browser window`
	})),
	{
		id: 'menu.settings.open',
		label: 'Open Settings',
		kind: 'action',
		parentId: 'menu',
		description: 'Open unified system settings'
	},
	{
		id: 'menu.software.open',
		label: 'Open Software',
		kind: 'action',
		parentId: 'menu',
		description: 'Browse and manage applications'
	},
	{
		id: 'control.bluetooth.toggle',
		label: 'Bluetooth',
		kind: 'toggle',
		parentId: 'panel.control',
		description: 'Toggle Bluetooth'
	},
	{
		id: 'control.dnd.toggle',
		label: 'Do Not Disturb',
		kind: 'toggle',
		parentId: 'panel.control',
		description: 'Mute notification popups'
	},
	{
		id: 'control.theme.toggle',
		label: 'Appearance',
		kind: 'toggle',
		parentId: 'panel.control',
		description: 'Toggle light and dark appearance'
	},
	{
		id: 'control.volume',
		label: 'Volume',
		kind: 'input',
		parentId: 'panel.control',
		description: 'Set output volume'
	},
	{
		id: 'control.brightness',
		label: 'Brightness',
		kind: 'input',
		parentId: 'panel.control',
		description: 'Set display brightness'
	},
	{
		id: 'notifications.clear',
		label: 'Clear notifications',
		kind: 'action',
		parentId: 'panel.control',
		description: 'Clear notification history'
	},
	{
		id: 'notifications.dismiss',
		label: 'Dismiss notification',
		kind: 'input',
		parentId: 'panel.control',
		description: 'Dismiss one notification'
	},
	{
		id: 'workspace.create',
		label: 'Create workspace',
		kind: 'input',
		parentId: 'panel.overview',
		description: 'Ensure a numbered workspace exists'
	},
	{
		id: 'workspace.switch',
		label: 'Switch workspace',
		kind: 'input',
		parentId: 'panel.overview',
		description: 'Switch to a numbered workspace'
	},
	{
		id: 'workspace.window.move',
		label: 'Move window',
		kind: 'input',
		parentId: 'panel.overview',
		description: 'Move a window to another workspace'
	},
	{
		id: 'window.snap',
		label: 'Snap window',
		kind: 'input',
		parentId: 'desktop',
		description: 'Snap a window to one side, optionally beside another window'
	},
	{
		id: 'browser.open',
		label: 'Open browser',
		kind: 'action',
		parentId: 'window.browser',
		description: 'Open the browser on the current workspace'
	},
	{
		id: 'browser.download',
		label: 'Download browser resource',
		kind: 'input',
		parentId: 'window.browser',
		description: 'Download the current page or another browser resource'
	},
	{
		id: 'editor.open',
		label: 'Open editor',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Open the editor on the current workspace'
	},
	{
		id: 'clipboard.copy',
		label: 'Copy item',
		kind: 'input',
		parentId: 'panel.clipboard',
		description: 'Put an item on the clipboard'
	},
	{
		id: 'clipboard.read',
		label: 'Read current item',
		kind: 'action',
		parentId: 'panel.clipboard',
		description: 'Read the current clipboard item into task working memory'
	},
	{
		id: 'filesystem.search',
		label: 'Search files',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Search the filesystem and capture the matching file in task working memory'
	},
	{
		id: 'filesystem.open_downloads',
		label: 'Open Downloads',
		kind: 'action',
		parentId: 'desktop.filesystem',
		description: 'Open the Downloads folder'
	},
	{
		id: 'filesystem.rename',
		label: 'Rename file',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Rename the file in task working memory'
	},
	{
		id: 'filesystem.move',
		label: 'Move file',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Move the file in task working memory to another folder'
	},
	{
		id: 'filesystem.star',
		label: 'Star file',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Set the starred state of the file in task working memory'
	},
	{
		id: 'filesystem.compress',
		label: 'Compress file',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Create an archive containing files from task working memory'
	},
	{
		id: 'filesystem.open_file',
		label: 'Open file',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Open a file found by its stable identifier or name'
	},
	{
		id: 'filesystem.reveal',
		label: 'Reveal file',
		kind: 'action',
		parentId: 'desktop.filesystem',
		description: 'Reveal the captured file in its parent folder'
	},
	{
		id: 'filesystem.open',
		label: 'Open folder',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Open Files at a semantic path'
	},
	{
		id: 'filesystem.create_folder',
		label: 'Create folder',
		kind: 'input',
		parentId: 'desktop.filesystem',
		description: 'Create a named folder under a parent path'
	},
	{
		id: 'editor.new_document',
		label: 'New document',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Create an empty editor document'
	},
	{
		id: 'editor.paste_content',
		label: 'Paste content',
		kind: 'input',
		parentId: 'window.editor',
		description: 'Paste supplied clipboard content into the active document'
	},
	{
		id: 'editor.save_as',
		label: 'Save document as',
		kind: 'input',
		parentId: 'window.editor',
		description: 'Save the active document with a name and parent path'
	},
	{
		id: 'editor.close_document',
		label: 'Close document',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Close the saved editor document'
	},
	{
		id: 'editor.insert',
		label: 'Insert text',
		kind: 'input',
		parentId: 'window.editor',
		description: 'Insert supplied text at the requested document position'
	},
	{
		id: 'editor.save',
		label: 'Save active document',
		kind: 'action',
		parentId: 'window.editor',
		description: 'Persist the active editor document'
	},
	{
		id: 'capture.save',
		label: 'Save capture',
		kind: 'input',
		parentId: 'panel.capture',
		description: 'Save a screen capture'
	},
	{
		id: 'software.toggle',
		label: 'Install or remove app',
		kind: 'input',
		parentId: 'window.software',
		description: 'Toggle application installation'
	},
	{
		id: 'files.path',
		label: 'Open path',
		kind: 'input',
		parentId: 'window.files',
		description: 'Browse to a folder'
	},
	{
		id: 'files.action',
		label: 'File action',
		kind: 'input',
		parentId: 'window.files',
		description: 'Perform a simulated file operation'
	},
	{
		id: 'files.create',
		label: 'Create file or folder',
		kind: 'input',
		parentId: 'window.files',
		description: 'Create an item with {name, kind, parent_path, content}'
	},
	{
		id: 'window.settings',
		label: 'Settings window',
		kind: 'window',
		parentId: 'desktop',
		description: 'Unified persistent system settings'
	},
	{
		id: 'window.settings.minimize',
		label: 'Minimize Settings',
		kind: 'action',
		parentId: 'window.settings',
		description: 'Minimize Settings'
	},
	{
		id: 'window.settings.maximize',
		label: 'Maximize Settings',
		kind: 'action',
		parentId: 'window.settings',
		description: 'Toggle Settings maximization'
	},
	{
		id: 'window.settings.close',
		label: 'Close Settings',
		kind: 'action',
		parentId: 'window.settings',
		description: 'Close Settings'
	},
	{
		id: 'window.software',
		label: 'Software window',
		kind: 'window',
		parentId: 'desktop',
		description: 'Install, update and remove software'
	},
	{
		id: 'window.software.minimize',
		label: 'Minimize Software',
		kind: 'action',
		parentId: 'window.software',
		description: 'Minimize Software'
	},
	{
		id: 'window.software.maximize',
		label: 'Maximize Software',
		kind: 'action',
		parentId: 'window.software',
		description: 'Toggle Software maximization'
	},
	{
		id: 'window.software.close',
		label: 'Close Software',
		kind: 'action',
		parentId: 'window.software',
		description: 'Close Software'
	},
	{
		id: 'window.terminal',
		label: 'Terminal window',
		kind: 'window',
		parentId: 'desktop',
		description: 'Terminal session'
	},
	{
		id: 'window.terminal.execute',
		label: 'Execute terminal command',
		kind: 'input',
		parentId: 'window.terminal',
		description: 'Execute a command in the virtual terminal'
	},
	{
		id: 'window.terminal.minimize',
		label: 'Minimize Terminal',
		kind: 'action',
		parentId: 'window.terminal',
		description: 'Minimize Terminal'
	},
	{
		id: 'window.terminal.maximize',
		label: 'Maximize Terminal',
		kind: 'action',
		parentId: 'window.terminal',
		description: 'Toggle Terminal maximization'
	},
	{
		id: 'window.terminal.close',
		label: 'Close Terminal',
		kind: 'action',
		parentId: 'window.terminal',
		description: 'Close Terminal'
	}
];

export const nodeById = new Map(controlGraph.map((node) => [node.id, node]));

export function childrenOf(parentId: string): ControlNode[] {
	return controlGraph.filter((node) => node.parentId === parentId);
}
