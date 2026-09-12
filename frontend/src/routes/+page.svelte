<script lang="ts">
	import { onMount } from 'svelte';
	import { formatFileMeta, osApi, type FileEntry } from '$lib/os/api';
	import { createOSRuntime } from '$lib/os/runtime';
	import type { OSCommand, WindowName } from '$lib/os/types';

	const runtime = createOSRuntime();
	const osState = runtime.state;
	const osEvents = runtime.events;
	let invokeValue = $state('panel.network');
	let clock = $state(new Date());
	let settingsSection = $state('Appearance');
	let softwareSearch = $state('');
	let fileSearch = $state('');
	let selectedFileId = $state<number | null>(null);
	let activeFileId = $state<number | null>(null);
	let activeFileName = $state('desktop-actions-notes.txt');
	let backendOnline = $state(false);
	let filesLoading = $state(false);
	let fileSearchTimer: ReturnType<typeof setTimeout> | undefined;

	const desktopIcons = [
		{ id: 'desktop.home', label: 'Home', icon: '/assets/icons/home.svg' },
		{ id: 'desktop.trash', label: 'Trash', icon: '/assets/icons/trash.svg' },
		{ id: 'desktop.filesystem', label: 'File System', icon: '/assets/icons/drive.svg' },
		{ id: 'desktop.research', label: 'Research', icon: '/assets/icons/folder.svg' }
	];

	const applications = [
		{
			id: 'menu.browser.open',
			label: 'Browser',
			note: 'Browse the web',
			icon: '/assets/icons/browser.svg'
		},
		{
			id: 'menu.editor.open',
			label: 'Text Editor',
			note: 'Edit plain text files',
			icon: '/assets/icons/editor.svg'
		},
		{
			id: 'menu.files.open',
			label: 'Files',
			note: 'Browse files and folders',
			icon: '/assets/icons/folder.svg'
		},
		{
			id: 'menu.terminal.open',
			label: 'Terminal',
			note: 'Use the command line',
			icon: '/assets/icons/terminal.svg'
		},
		{
			id: 'menu.settings.open',
			label: 'Settings',
			note: 'Configure your system',
			icon: '/assets/icons/settings.svg'
		},
		{
			id: 'menu.software.open',
			label: 'Software',
			note: 'Install and update apps',
			icon: '/assets/icons/drive.svg'
		}
	];

	let files = $state<FileEntry[]>([
		{
			id: -1,
			parent_id: null,
			name: 'Desktop',
			kind: 'folder',
			mime_type: null,
			size: 0,
			starred: false,
			deleted: false,
			created_at: '',
			updated_at: '',
			path: '/home/agentos/Desktop'
		},
		{
			id: -2,
			parent_id: null,
			name: 'Documents',
			kind: 'folder',
			mime_type: null,
			size: 0,
			starred: false,
			deleted: false,
			created_at: '',
			updated_at: '',
			path: '/home/agentos/Documents'
		},
		{
			id: -3,
			parent_id: null,
			name: 'Downloads',
			kind: 'folder',
			mime_type: null,
			size: 0,
			starred: false,
			deleted: false,
			created_at: '',
			updated_at: '',
			path: '/home/agentos/Downloads'
		},
		{
			id: -4,
			parent_id: null,
			name: 'Pictures',
			kind: 'folder',
			mime_type: null,
			size: 0,
			starred: false,
			deleted: false,
			created_at: '',
			updated_at: '',
			path: '/home/agentos/Pictures'
		},
		{
			id: -5,
			parent_id: null,
			name: 'Research',
			kind: 'folder',
			mime_type: null,
			size: 0,
			starred: false,
			deleted: false,
			created_at: '',
			updated_at: '',
			path: '/home/agentos/Documents/Research'
		},
		{
			id: -6,
			parent_id: null,
			name: 'desktop-actions-notes.txt',
			kind: 'text',
			mime_type: 'text/plain',
			size: 2100,
			starred: false,
			deleted: false,
			created_at: '',
			updated_at: '',
			path: '/home/agentos/Documents/Research/desktop-actions-notes.txt'
		}
	]);
	const visibleFiles = $derived(
		files.filter((file) => file.name.toLowerCase().includes(fileSearch.toLowerCase()))
	);
	const selectedFile = $derived(files.find((file) => file.id === selectedFileId) ?? null);
	const software = [
		{ name: 'Firefox', category: 'Web', rating: '4.8', description: 'Fast, private web browser' },
		{
			name: 'LibreOffice',
			category: 'Productivity',
			rating: '4.6',
			description: 'Documents, sheets and presentations'
		},
		{
			name: 'VLC',
			category: 'Audio & Video',
			rating: '4.9',
			description: 'Play virtually any media file'
		},
		{
			name: 'Krita',
			category: 'Graphics',
			rating: '4.7',
			description: 'Professional digital painting'
		},
		{ name: 'Signal', category: 'Communication', rating: '4.8', description: 'Private messaging' }
	];
	const visibleSoftware = $derived(
		software.filter((app) =>
			`${app.name} ${app.category}`.toLowerCase().includes(softwareSearch.toLowerCase())
		)
	);

	const filteredApplications = $derived(
		applications.filter((app) =>
			`${app.label} ${app.note}`.toLowerCase().includes($osState.menuSearch.toLowerCase())
		)
	);
	const filteredEvents = $derived(
		$osEvents.filter((event) =>
			`${event.node} ${event.source} ${event.detail}`
				.toLowerCase()
				.includes($osState.inspectorQuery.toLowerCase())
		)
	);
	const filteredNodes = $derived(
		runtime.graph.filter((node) =>
			`${node.id} ${node.label} ${node.kind}`
				.toLowerCase()
				.includes($osState.inspectorQuery.toLowerCase())
		)
	);

	onMount(() => {
		const timer = window.setInterval(() => (clock = new Date()), 1000);
		const stream = new EventSource('/api/control');
		let backendStream: EventSource | undefined;
		let loadedPath = '';
		const unsubscribeState = osState.subscribe((current) => {
			if (backendOnline && current.filesPath !== loadedPath) {
				loadedPath = current.filesPath;
				void loadFiles(current.filesPath);
			}
		});
		void runtime.initialize().then((connected) => {
			backendOnline = connected;
			if (!connected) return;
			loadedPath = runtime.snapshot().filesPath;
			void loadFiles(loadedPath);
			backendStream = osApi.commandStream();
			backendStream.addEventListener(
				'command',
				(event) =>
					void runtime.dispatch(JSON.parse((event as MessageEvent).data) as OSCommand, 'remote')
			);
		});
		stream.addEventListener(
			'command',
			(event) =>
				void runtime.dispatch(JSON.parse((event as MessageEvent).data) as OSCommand, 'remote')
		);
		const receiveCommand = (event: Event) => {
			const detail = (event as CustomEvent<OSCommand>).detail;
			if (detail?.node) void runtime.dispatch(detail, detail.source ?? 'remote');
		};
		const receiveMessage = (event: MessageEvent) => {
			if (event.data?.type === 'agentos:command' && event.data.command?.node)
				void runtime.dispatch(event.data.command, 'remote');
		};
		window.addEventListener('agentos:command', receiveCommand);
		window.addEventListener('message', receiveMessage);
		const keyboard = (event: KeyboardEvent) => {
			if (event.key === 'Meta' || (event.ctrlKey && event.code === 'Space')) {
				event.preventDefault();
				void runtime.dispatch('panel.menu');
			}
			if (event.altKey && event.key === 'Tab') {
				event.preventDefault();
				void runtime.dispatch('panel.overview');
			}
			if (event.key === 'PrintScreen') void runtime.dispatch('panel.capture');
			if (event.key === 'Escape' && $osState.overlay)
				void runtime.dispatch(
					`panel.${$osState.overlay === 'launcher' ? 'menu' : $osState.overlay}`
				);
		};
		window.addEventListener('keydown', keyboard);
		(window as unknown as { agentOS: unknown }).agentOS = {
			dispatch: (command: OSCommand | string) => runtime.dispatch(command, 'remote'),
			listNodes: () => runtime.graph,
			snapshot: runtime.snapshot
		};
		console.info('AgentOS ready', {
			endpoint: '/api/control',
			nodes: runtime.graph.length,
			api: 'window.agentOS'
		});
		return () => {
			window.clearInterval(timer);
			stream.close();
			backendStream?.close();
			unsubscribeState();
			window.removeEventListener('agentos:command', receiveCommand);
			window.removeEventListener('message', receiveMessage);
			window.removeEventListener('keydown', keyboard);
		};
	});

	function beginDrag(event: PointerEvent, name: WindowName) {
		if ($osState.windows[name].maximized || (event.target as HTMLElement).closest('button')) return;
		void runtime.dispatch(`window.${name}`, 'human');
		const start = $osState.windows[name];
		const offsetX = event.clientX - start.x;
		const offsetY = event.clientY - start.y;
		const move = (moveEvent: PointerEvent) =>
			runtime.moveWindow(
				name,
				Math.max(0, moveEvent.clientX - offsetX),
				Math.max(0, moveEvent.clientY - offsetY)
			);
		const end = () => {
			window.removeEventListener('pointermove', move);
			window.removeEventListener('pointerup', end);
			console.debug('AgentOS window moved', {
				window: name,
				position: runtime.snapshot().windows[name]
			});
		};
		window.addEventListener('pointermove', move);
		window.addEventListener('pointerup', end, { once: true });
	}

	function windowStyle(name: WindowName): string {
		const current = $osState.windows[name];
		return current.maximized
			? `z-index:${current.z}`
			: `left:${current.x}px;top:${current.y}px;z-index:${current.z}`;
	}

	function isVisible(name: WindowName) {
		const item = $osState.windows[name];
		return item.open && !item.minimized && item.workspace === $osState.workspace;
	}

	async function invokeNode() {
		const raw = invokeValue.trim();
		if (!raw) return;
		let command: OSCommand = { node: raw };
		if (raw.startsWith('{')) {
			try {
				command = JSON.parse(raw) as OSCommand;
			} catch {
				command = { node: raw };
			}
		}
		await runtime.dispatch(command, 'human');
	}

	async function loadFiles(path = $osState.filesPath, query = '') {
		if (!backendOnline) return;
		filesLoading = true;
		try {
			files = query.trim() ? await osApi.searchFiles(query.trim()) : await osApi.listFiles(path);
			selectedFileId = null;
		} catch (error) {
			await runtime.dispatch(
				{
					node: 'files.action',
					input: error instanceof Error ? error.message : 'Unable to load files'
				},
				'system'
			);
		} finally {
			filesLoading = false;
		}
	}

	async function openPath(path: string) {
		await runtime.dispatch({ node: 'files.path', input: path });
		await loadFiles(path);
	}

	async function openFile(file: FileEntry) {
		if (file.kind === 'folder') return openPath(file.path);
		if (file.kind !== 'text') {
			await runtime.dispatch({ node: 'files.action', input: `Opened ${file.name}` });
			return;
		}
		try {
			const loaded = await osApi.getFile(file.id, true);
			activeFileId = loaded.id;
			activeFileName = loaded.name;
			await runtime.dispatch({ node: 'window.editor.text', input: loaded.content ?? '' });
			await runtime.dispatch('menu.editor.open');
		} catch (error) {
			await runtime.dispatch(
				{
					node: 'files.action',
					input: error instanceof Error ? error.message : 'Unable to open file'
				},
				'system'
			);
		}
	}

	async function saveDocument() {
		if (!backendOnline || activeFileId === null) {
			await runtime.dispatch({ node: 'files.action', input: 'Document kept in desktop state' });
			return;
		}
		await osApi.saveFile(activeFileId, $osState.editorText);
		await runtime.dispatch({ node: 'files.action', input: `Saved ${activeFileName}` });
	}

	async function createFolder() {
		if (!backendOnline)
			return void runtime.dispatch({ node: 'files.action', input: 'Backend is offline' });
		const name = window.prompt('Folder name', 'New Folder')?.trim();
		if (!name) return;
		try {
			await osApi.createFile({ parent_path: $osState.filesPath, name, kind: 'folder' });
			await loadFiles();
			await runtime.dispatch({ node: 'files.action', input: `Created ${name}` });
		} catch (error) {
			await runtime.dispatch(
				{
					node: 'files.action',
					input: error instanceof Error ? error.message : 'Unable to create folder'
				},
				'system'
			);
		}
	}

	async function renameSelected() {
		if (!selectedFile || selectedFile.id < 0) return;
		const oldName = selectedFile.name;
		const name = window.prompt('New name', oldName)?.trim();
		if (!name || name === oldName) return;
		await osApi.updateFile(selectedFile.id, { name });
		await loadFiles();
		await runtime.dispatch({ node: 'files.action', input: `Renamed ${oldName} to ${name}` });
	}

	async function trashSelected() {
		if (!selectedFile || selectedFile.id < 0) return;
		const { id, name } = selectedFile;
		await osApi.trashFile(id);
		await loadFiles();
		await runtime.dispatch({ node: 'files.action', input: `Moved ${name} to Trash` });
	}

	async function restoreSelected() {
		if (!selectedFile || selectedFile.id < 0) return;
		const { id, name } = selectedFile;
		await osApi.restoreFile(id);
		await loadFiles();
		await runtime.dispatch({ node: 'files.action', input: `Restored ${name}` });
	}

	function searchFiles(value: string) {
		fileSearch = value;
		if (!backendOnline) return;
		if (fileSearchTimer) clearTimeout(fileSearchTimer);
		fileSearchTimer = setTimeout(() => void loadFiles($osState.filesPath, value), 180);
	}
</script>

<svelte:head
	><title>AgentOS Research Desktop</title><meta
		name="description"
		content="A graph-native simulated desktop environment"
	/></svelte:head
>

<main
	class:light-theme={!$osState.darkMode}
	class="desktop"
	aria-label="AgentOS desktop"
	style={`--screen-brightness:${$osState.brightness}%`}
>
	<section class="desktop-icons" aria-label="Desktop items">
		{#each desktopIcons as item (item.id)}
			<button
				class="desktop-icon"
				ondblclick={() => runtime.dispatch(item.id)}
				onclick={() => console.debug('AgentOS desktop selection', item.id)}
				aria-label={`Open ${item.label}`}
			>
				<img src={item.icon} alt="" /><span>{item.label}</span>
			</button>
		{/each}
	</section>

	{#if isVisible('editor')}
		<section
			class:maximized={$osState.windows.editor.maximized}
			class="window editor-window"
			style={windowStyle('editor')}
			aria-label="Text Editor window"
			onpointerdown={() => runtime.dispatch('window.editor')}
		>
			<header
				class="titlebar"
				role="toolbar"
				tabindex="-1"
				onpointerdown={(event) => beginDrag(event, 'editor')}
			>
				<div class="window-title">
					{activeFileName} <span>— ~/Documents/Research</span>
				</div>
				<div class="window-controls">
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.editor.minimize');
						}}
						aria-label="Minimize Text Editor"
						><img src="/assets/icons/window-minimize.svg" alt="" /></button
					>
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.editor.maximize');
						}}
						aria-label="Maximize Text Editor"
						><img src="/assets/icons/window-maximize.svg" alt="" /></button
					>
					<button
						class="close"
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.editor.close');
						}}
						aria-label="Close Text Editor"
						><img src="/assets/icons/window-close.svg" alt="" /></button
					>
				</div>
			</header>
			<nav class="menubar" aria-label="Editor menus">
				<button>File</button><button>Edit</button><button>View</button><button>Search</button
				><button>Tools</button><button>Documents</button><button>Help</button>
			</nav>
			<div class="toolbar" aria-label="Editor toolbar">
				<button title="New document"><img src="/assets/icons/document-new.svg" alt="" /></button
				><button title="Save document" onclick={saveDocument}
					><img src="/assets/icons/document-save.svg" alt="" /></button
				><span class="tool-separator"></span><button title="Undo"
					><img src="/assets/icons/edit-undo.svg" alt="" /></button
				><button title="Redo"><img src="/assets/icons/edit-redo.svg" alt="" /></button><span
					class="format-label">Plain Text</span
				><img class="chevron" src="/assets/icons/go-down.svg" alt="" /><span class="tool-separator"
				></span><span class="format-label">Spaces: 4</span>
			</div>
			<div class="document-tab">
				<img src="/assets/icons/editor.svg" alt="" /><span>desktop-actions-notes.txt</span><button
					aria-label="Close tab"><img src="/assets/icons/window-close.svg" alt="" /></button
				>
			</div>
			<div class="editor-body">
				<div class="line-numbers" aria-hidden="true">
					{#each Array.from({ length: 26 }, (_, index) => index + 1) as line (line)}<span
							>{line}</span
						>{/each}
				</div>
				<textarea
					aria-label="Research notes"
					spellcheck="false"
					value={$osState.editorText}
					oninput={(event) =>
						runtime.dispatch({ node: 'window.editor.text', input: event.currentTarget.value })}
				></textarea>
			</div>
			<footer class="statusbar">
				<span>Plain Text</span><span>Tab Width: 4</span><span>Ln 26, Col 1</span>
			</footer>
		</section>
	{/if}

	{#if isVisible('inspector')}
		<section
			class:maximized={$osState.windows.inspector.maximized}
			class="window inspector-window"
			style={windowStyle('inspector')}
			aria-label="Control Graph Inspector window"
			onpointerdown={() => runtime.dispatch('window.inspector')}
		>
			<header
				class="titlebar"
				role="toolbar"
				tabindex="-1"
				onpointerdown={(event) => beginDrag(event, 'inspector')}
			>
				<div class="window-title">Control Graph Inspector</div>
				<div class="window-controls">
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.inspector.minimize');
						}}
						aria-label="Minimize Inspector"
						><img src="/assets/icons/window-minimize.svg" alt="" /></button
					><button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.inspector.maximize');
						}}
						aria-label="Maximize Inspector"
						><img src="/assets/icons/window-maximize.svg" alt="" /></button
					><button
						class="close"
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.inspector.close');
						}}
						aria-label="Close Inspector"><img src="/assets/icons/window-close.svg" alt="" /></button
					>
				</div>
			</header>
			<nav class="inspector-tabs" aria-label="Inspector sections">
				{#each ['events', 'nodes', 'state', 'settings'] as tab (tab)}<button
						class:active={$osState.inspectorTab === tab}
						onclick={() => runtime.dispatch(`window.inspector.tab.${tab}`)}
						>{tab[0].toUpperCase() + tab.slice(1)}</button
					>{/each}
			</nav>
			<label class="search-box"
				><img src="/assets/icons/search.svg" alt="" /><input
					aria-label="Filter inspector"
					placeholder={`Search ${$osState.inspectorTab}…`}
					value={$osState.inspectorQuery}
					oninput={(event) =>
						runtime.dispatch({ node: 'window.inspector.query', input: event.currentTarget.value })}
				/></label
			>
			<div class="inspector-content">
				{#if $osState.inspectorTab === 'events'}
					<table class="event-table">
						<thead><tr><th>Time</th><th>Source</th><th>Node / Action</th><th>Result</th></tr></thead
						><tbody
							>{#each filteredEvents as event (event.id)}<tr title={event.detail}
									><td>{event.time}</td><td>{event.source}</td><td>{event.node}</td><td
										><span class:error-dot={event.result === 'error'} class="result-dot"></span></td
									></tr
								>{/each}</tbody
						>
					</table>
				{:else if $osState.inspectorTab === 'nodes'}
					<div class="node-list">
						{#each filteredNodes as node (node.id)}<button onclick={() => (invokeValue = node.id)}
								><span>{node.id}</span><small>{node.kind} · {node.description}</small></button
							>{/each}
					</div>
				{:else if $osState.inspectorTab === 'state'}<pre class="state-view">{JSON.stringify(
							$osState,
							null,
							2
						)}</pre>
				{:else}<div class="settings-view">
						<label><input type="checkbox" checked /> Log human actions</label><label
							><input type="checkbox" checked /> Log remote actions</label
						><label><input type="checkbox" checked /> Mirror state to console</label>
						<p>Transport: Server-Sent Events<br />Endpoint: <code>/api/control</code></p>
					</div>{/if}
			</div>
			<div class="focused-node">
				<span>Current focused node</span><code>{$osState.focusedNode}</code>
			</div>
			<div class="invoke-bar">
				<label for="invoke-node">Invoke node</label>
				<div>
					<input
						id="invoke-node"
						bind:value={invokeValue}
						onkeydown={(event) => event.key === 'Enter' && void invokeNode()}
						spellcheck="false"
					/><button onclick={invokeNode}>Run</button>
				</div>
			</div>
			<footer class="inspector-status">
				<span><i></i> listening</span><span
					>{$osEvents.length} events · {runtime.graph.length} nodes</span
				>
			</footer>
		</section>
	{/if}

	{#if isVisible('files')}
		<section
			class:maximized={$osState.windows.files.maximized}
			class="window files-window"
			style={windowStyle('files')}
			aria-label="Files window"
			onpointerdown={() => runtime.dispatch('window.files')}
		>
			<header
				class="titlebar"
				role="toolbar"
				tabindex="-1"
				onpointerdown={(event) => beginDrag(event, 'files')}
			>
				<div class="window-title">{$osState.filesPath}</div>
				<div class="window-controls">
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.files.minimize');
						}}
						aria-label="Minimize Files"
						><img src="/assets/icons/window-minimize.svg" alt="" /></button
					>
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.files.maximize');
						}}
						aria-label="Maximize Files"
						><img src="/assets/icons/window-maximize.svg" alt="" /></button
					>
					<button
						class="close"
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.files.close');
						}}
						aria-label="Close Files"><img src="/assets/icons/window-close.svg" alt="" /></button
					>
				</div>
			</header>
			<div class="files-toolbar">
				<button aria-label="Back"><img src="/assets/icons/go-previous.svg" alt="" /></button><button
					aria-label="Forward"><img src="/assets/icons/go-next.svg" alt="" /></button
				><span><img src="/assets/icons/go-home.svg" alt="" /> {$osState.filesPath}</span>
				<label class="files-search"
					><img src="/assets/icons/search.svg" alt="" /><input
						aria-label="Search files"
						placeholder="Search"
						value={fileSearch}
						oninput={(event) => searchFiles(event.currentTarget.value)}
					/></label
				>
				<button class="new-button" onclick={createFolder}>+ New</button>
			</div>
			<div class="files-body">
				<aside>
					<strong>Places</strong>
					{#each ['Home', 'Desktop', 'Documents', 'Downloads', 'Recent', 'Starred', 'Trash'] as place (place)}<button
							class:active={$osState.filesPath === place}
							onclick={() => openPath(place)}>{place}</button
						>{/each}
					<strong>Devices</strong><button onclick={() => openPath('Archive USB')}
						>Archive USB <small>32 GB</small></button
					>
				</aside>
				<div class="files-main">
					<div class="files-heading">
						<div>
							<strong>{$osState.filesPath}</strong><small
								>{filesLoading
									? 'Loading…'
									: `${visibleFiles.length} items · sorted by name`}</small
							>
						</div>
						<button aria-label="Grid view">▦</button><button aria-label="Sort files">↕</button>
					</div>
					<div class="folder-grid">
						{#each visibleFiles as file (file.id)}<button
								class:selected={selectedFileId === file.id}
								onclick={() => (selectedFileId = file.id)}
								ondblclick={() => openFile(file)}
							>
								<img
									src={file.kind === 'folder'
										? '/assets/icons/folder.svg'
										: file.kind === 'text'
											? '/assets/icons/editor.svg'
											: '/assets/icons/drive.svg'}
									alt=""
								/><span>{file.name}</span><small>{formatFileMeta(file)}</small>
							</button>{/each}
					</div>
					{#if selectedFile}<div class="file-actions">
							<span>{selectedFile.name}</span><button
								onclick={() =>
									runtime.dispatch({ node: 'clipboard.copy', input: selectedFile.path })}
								>Share</button
							><button onclick={renameSelected}>Rename</button
							>{#if $osState.filesPath === 'Trash'}<button onclick={restoreSelected}>Restore</button
								>{:else}<button onclick={trashSelected}>Trash</button>{/if}
							>
						</div>{/if}
				</div>
			</div>
		</section>
	{/if}

	{#if isVisible('settings')}
		<section
			class:maximized={$osState.windows.settings.maximized}
			class="window settings-window"
			style={windowStyle('settings')}
			aria-label="Settings window"
			onpointerdown={() => runtime.dispatch('window.settings')}
		>
			<header
				class="titlebar"
				role="toolbar"
				tabindex="-1"
				onpointerdown={(event) => beginDrag(event, 'settings')}
			>
				<div class="window-title">Settings</div>
				<div class="window-controls">
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.settings.minimize');
						}}
						aria-label="Minimize Settings"
						><img src="/assets/icons/window-minimize.svg" alt="" /></button
					>
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.settings.maximize');
						}}
						aria-label="Maximize Settings"
						><img src="/assets/icons/window-maximize.svg" alt="" /></button
					>
					<button
						class="close"
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.settings.close');
						}}
						aria-label="Close Settings"><img src="/assets/icons/window-close.svg" alt="" /></button
					>
				</div>
			</header>
			<div class="settings-shell">
				<aside class="settings-sidebar">
					<label
						><img src="/assets/icons/search.svg" alt="" /><input
							aria-label="Search settings"
							placeholder="Search settings"
						/></label
					>
					{#each ['Network', 'Bluetooth', 'Displays', 'Sound', 'Appearance', 'Applications', 'Notifications', 'Keyboard', 'Mouse & Touchpad', 'Accessibility', 'Date & Language', 'Users'] as section (section)}
						<button
							class:active={settingsSection === section}
							onclick={() => (settingsSection = section)}>{section}</button
						>
					{/each}
				</aside>
				<div class="settings-content">
					<p class="eyebrow">SYSTEM SETTINGS</p>
					<h1>{settingsSection}</h1>
					{#if settingsSection === 'Appearance'}
						<div class="setting-card">
							<h2>Colour scheme</h2>
							<p>Use a consistent appearance across the desktop and apps.</p>
							<div class="theme-options">
								<button
									class:chosen={!$osState.darkMode}
									onclick={() => $osState.darkMode && runtime.dispatch('control.theme.toggle')}
									><i class="light-preview"></i>Light</button
								><button
									class:chosen={$osState.darkMode}
									onclick={() => !$osState.darkMode && runtime.dispatch('control.theme.toggle')}
									><i class="dark-preview"></i>Dark</button
								>
							</div>
						</div>
						<div class="setting-card row-setting">
							<div>
								<h2>Accent colour</h2>
								<p>Used for selections and active controls.</p>
							</div>
							<div class="swatches"><i></i><i></i><i></i><i></i></div>
						</div>
						<div class="setting-card row-setting">
							<div>
								<h2>Text size</h2>
								<p>Default · 100%</p>
							</div>
							<input aria-label="Text size" type="range" min="80" max="150" value="100" />
						</div>
					{:else if settingsSection === 'Applications'}
						<div class="setting-card">
							<h2>Default applications</h2>
							{#each [['Web', 'Firefox'], ['Text', 'Text Editor'], ['Photos', 'Image Viewer'], ['Video', 'VLC'], ['PDF', 'Document Viewer'], ['Terminal', 'Terminal']] as item (item[0])}<div
									class="default-row"
								>
									<span>{item[0]}</span><button>{item[1]}⌄</button>
								</div>{/each}
						</div>
					{:else if settingsSection === 'Accessibility'}
						<div class="setting-card">
							<h2>Seeing</h2>
							{#each ['High contrast', 'Large text', 'Screen reader', 'Magnifier'] as item (item)}<label
									class="toggle-row"><span>{item}</span><input type="checkbox" /></label
								>{/each}
						</div>
						<div class="setting-card">
							<h2>Typing & motion</h2>
							{#each ['Sticky keys', 'Slow keys', 'Reduce motion'] as item (item)}<label
									class="toggle-row"><span>{item}</span><input type="checkbox" /></label
								>{/each}
						</div>
					{:else}
						<div class="setting-card">
							<h2>{settingsSection}</h2>
							<p>Manage {settingsSection.toLowerCase()} preferences from one place.</p>
							{#each ['Primary device', 'Automatic configuration', 'Remember this setting'] as item (item)}<label
									class="toggle-row"
									><span>{item}</span><input
										type="checkbox"
										checked={item !== 'Primary device'}
									/></label
								>{/each}
						</div>
					{/if}
				</div>
			</div>
		</section>
	{/if}

	{#if isVisible('software')}
		<section
			class:maximized={$osState.windows.software.maximized}
			class="window software-window"
			style={windowStyle('software')}
			aria-label="Software window"
			onpointerdown={() => runtime.dispatch('window.software')}
		>
			<header
				class="titlebar"
				role="toolbar"
				tabindex="-1"
				onpointerdown={(event) => beginDrag(event, 'software')}
			>
				<div class="window-title">Software</div>
				<div class="window-controls">
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.software.minimize');
						}}
						aria-label="Minimize Software"
						><img src="/assets/icons/window-minimize.svg" alt="" /></button
					><button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.software.maximize');
						}}
						aria-label="Maximize Software"
						><img src="/assets/icons/window-maximize.svg" alt="" /></button
					><button
						class="close"
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.software.close');
						}}
						aria-label="Close Software"><img src="/assets/icons/window-close.svg" alt="" /></button
					>
				</div>
			</header>
			<div class="software-top">
				<div>
					<h1>Discover software</h1>
					<p>Arch repositories and Flatpak, together.</p>
				</div>
				<label
					><img src="/assets/icons/search.svg" alt="" /><input
						aria-label="Search software"
						placeholder="Search software"
						bind:value={softwareSearch}
					/></label
				>
			</div>
			<nav class="software-tabs">
				<button class="active">Explore</button><button
					>Installed <span>{$osState.installedApps.length}</span></button
				><button>Updates <span>3</span></button>
			</nav>
			<div class="featured-app">
				<div class="feature-icon">✦</div>
				<div>
					<small>EDITOR'S CHOICE</small>
					<h2>Build your perfect workspace</h2>
					<p>Useful tools, curated for AgentOS and verified for your system.</p>
				</div>
				<button>Explore collection</button>
			</div>
			<div class="software-list">
				<h2>Popular applications</h2>
				{#each visibleSoftware as app (app.name)}<article>
						<div class="app-monogram">{app.name[0]}</div>
						<div>
							<strong>{app.name}</strong>
							<p>{app.description}</p>
							<small>{app.category} · ★ {app.rating}</small>
						</div>
						<button
							class:installed={$osState.installedApps.includes(app.name)}
							onclick={() => runtime.dispatch({ node: 'software.toggle', input: app.name })}
							>{$osState.installedApps.includes(app.name) ? 'Remove' : 'Install'}</button
						>
					</article>{/each}
			</div>
		</section>
	{/if}

	{#if isVisible('terminal')}
		<section
			class:maximized={$osState.windows.terminal.maximized}
			class="window terminal-window"
			style={windowStyle('terminal')}
			aria-label="Terminal window"
			onpointerdown={() => runtime.dispatch('window.terminal')}
		>
			<header
				class="titlebar"
				role="toolbar"
				tabindex="-1"
				onpointerdown={(event) => beginDrag(event, 'terminal')}
			>
				<div class="window-title">Terminal — researcher@agentos</div>
				<div class="window-controls">
					<button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.terminal.minimize');
						}}
						aria-label="Minimize Terminal"
						><img src="/assets/icons/window-minimize.svg" alt="" /></button
					><button
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.terminal.maximize');
						}}
						aria-label="Maximize Terminal"
						><img src="/assets/icons/window-maximize.svg" alt="" /></button
					><button
						class="close"
						onclick={(event) => {
							event.stopPropagation();
							runtime.dispatch('window.terminal.close');
						}}
						aria-label="Close Terminal"><img src="/assets/icons/window-close.svg" alt="" /></button
					>
				</div>
			</header>
			<div class="terminal-body">
				<p>AgentOS 0.4.0 <span>· Arch Linux</span></p>
				<p>
					Last login: Today at {clock.toLocaleTimeString([], {
						hour: '2-digit',
						minute: '2-digit'
					})}
				</p>
				<label
					><strong>researcher@agentos</strong><span> ~ $ </span><input
						aria-label="Terminal command"
					/></label
				>
			</div>
		</section>
	{/if}

	{#if $osState.overlay === 'launcher'}
		<div
			class="overlay-scrim"
			role="presentation"
			onclick={() => runtime.dispatch('panel.menu')}
		></div>
		<section class="command-centre" aria-label="Application menu">
			<label class="global-search"
				><img src="/assets/icons/search.svg" alt="" /><input
					aria-label="Search applications"
					placeholder="Search apps, files, settings and actions…"
					value={$osState.menuSearch}
					oninput={(event) =>
						runtime.dispatch({ node: 'menu.search', input: event.currentTarget.value })}
				/><kbd>esc</kbd></label
			>
			<div class="search-layout">
				<aside>
					<button class="active">All</button><button>Applications</button><button>Files</button
					><button>Settings</button><button>Actions</button><span></span><button>Recent</button>
				</aside>
				<div class="search-results">
					<p class="section-label">APPLICATIONS</p>
					<div class="launcher-apps">
						{#each filteredApplications as app (app.id)}<button
								onclick={() => runtime.dispatch(app.id)}
								><img src={app.icon} alt="" /><span>{app.label}</span><small>{app.note}</small
								></button
							>{/each}
					</div>
					<p class="section-label">RECENT FILES</p>
					{#each files
						.filter((file) => file.kind !== 'folder')
						.filter((file) => file.name
								.toLowerCase()
								.includes($osState.menuSearch.toLowerCase())) as file (file.name)}<button
							class="search-result"
							onclick={() => {
								runtime.dispatch('menu.files.open');
								selectedFileId = file.id;
							}}
							><img
								src={file.kind === 'text' ? '/assets/icons/editor.svg' : '/assets/icons/drive.svg'}
								alt=""
							/><span
								><strong>{file.name}</strong><small>{file.path} · {formatFileMeta(file)}</small
								></span
							><kbd>↵</kbd></button
						>{/each}
					<p class="section-label">QUICK ACTIONS</p>
					<div class="quick-actions">
						<button onclick={() => runtime.dispatch('panel.capture')}>▣ Screenshot</button><button
							onclick={() => runtime.dispatch('menu.settings.open')}>⚙ Settings</button
						><button onclick={() => runtime.dispatch('panel.power')}>⏻ Power</button>
					</div>
				</div>
			</div>
			<footer>
				<span><kbd>↑</kbd><kbd>↓</kbd> navigate</span><span><kbd>Enter</kbd> open</span><span
					>Search replaces menus, not capability.</span
				>
			</footer>
		</section>
	{/if}

	{#if $osState.overlay === 'overview'}
		<div class="overview" aria-label="Workspace overview">
			<header>
				<div>
					<p class="eyebrow">OVERVIEW</p>
					<h1>Your workspace</h1>
				</div>
				<button onclick={() => runtime.dispatch('panel.menu')}
					><img src="/assets/icons/search.svg" alt="" /> Search</button
				>
			</header>
			<div class="workspace-strip">
				{#each [1, 2, 3, 4] as workspace (workspace)}<button
						class:active={$osState.workspace === workspace}
						onclick={() => runtime.dispatch({ node: 'workspace.switch', input: workspace })}
						><span class="workspace-mini"
							><i></i>{#each Object.entries($osState.windows)
								.filter(([, value]) => value.open && value.workspace === workspace)
								.slice(0, 3) as [previewName, value] (previewName)}<b
									style={`left:${Math.min(72, value.x / 16)}%;top:${Math.min(65, value.y / 12)}%`}
								></b>{/each}</span
						><strong>{workspace}</strong><small
							>{workspace === $osState.workspace
								? 'Current'
								: `${Object.values($osState.windows).filter((item) => item.open && item.workspace === workspace).length} windows`}</small
						></button
					>{/each}<button class="add-workspace">＋<small>New</small></button>
			</div>
			<div class="open-windows">
				<p class="section-label">OPEN WINDOWS</p>
				<div>
					{#each Object.entries($osState.windows).filter(([, value]) => value.open) as [name, value] (name)}<article
						>
							<button
								class="window-preview"
								onclick={() => {
									runtime.dispatch({ node: 'workspace.switch', input: value.workspace });
									runtime.dispatch(`window.${name}`);
								}}
								><span class="preview-bar"><i></i><i></i><i></i></span><strong
									>{name === 'inspector'
										? 'Control Graph'
										: name[0].toUpperCase() + name.slice(1)}</strong
								><small>Workspace {value.workspace}</small></button
							>
							<div class="move-window">
								Move to {#each [1, 2, 3, 4] as workspace (workspace)}<button
										class:active={value.workspace === workspace}
										onclick={() =>
											runtime.dispatch({
												node: 'workspace.window.move',
												input: { window: name, workspace }
											})}>{workspace}</button
									>{/each}
							</div>
						</article>{/each}
				</div>
			</div>
			<button class="close-overview" onclick={() => runtime.dispatch('panel.overview')}
				>Close overview <kbd>Esc</kbd></button
			>
		</div>
	{/if}

	{#if $osState.overlay === 'control'}
		<section class="control-centre" aria-label="Control Centre">
			<header>
				<div>
					<p class="eyebrow">CONTROL CENTRE</p>
					<h2>Quick settings</h2>
				</div>
				<button onclick={() => runtime.dispatch('menu.settings.open')}>All settings</button>
			</header>
			<div class="quick-grid">
				<button class:active={$osState.wifiEnabled} onclick={() => runtime.dispatch('wifi.toggle')}
					><i>◉</i><span
						><strong>Wi-Fi</strong><small>{$osState.connectedNetwork ?? 'Off'}</small></span
					></button
				><button
					class:active={$osState.bluetoothEnabled}
					onclick={() => runtime.dispatch('control.bluetooth.toggle')}
					><i>ᛒ</i><span
						><strong>Bluetooth</strong><small>{$osState.bluetoothEnabled ? 'On' : 'Off'}</small
						></span
					></button
				><button
					class:active={$osState.doNotDisturb}
					onclick={() => runtime.dispatch('control.dnd.toggle')}
					><i>☾</i><span
						><strong>Do Not Disturb</strong><small>{$osState.doNotDisturb ? 'On' : 'Off'}</small
						></span
					></button
				><button
					class:active={!$osState.darkMode}
					onclick={() => runtime.dispatch('control.theme.toggle')}
					><i>◐</i><span
						><strong>Appearance</strong><small>{$osState.darkMode ? 'Dark' : 'Light'}</small></span
					></button
				>
			</div>
			<label class="slider-row"
				><span>☀</span><input
					aria-label="Brightness"
					type="range"
					min="10"
					max="100"
					value={$osState.brightness}
					oninput={(event) =>
						runtime.dispatch({ node: 'control.brightness', input: event.currentTarget.value })}
				/><strong>{$osState.brightness}%</strong></label
			><label class="slider-row"
				><span>◕</span><input
					aria-label="Volume"
					type="range"
					min="0"
					max="100"
					value={$osState.volume}
					oninput={(event) =>
						runtime.dispatch({ node: 'control.volume', input: event.currentTarget.value })}
				/><strong>{$osState.volume}%</strong></label
			>
			<div class="notification-head">
				<h2>Notifications <span>{$osState.notifications.length}</span></h2>
				{#if $osState.notifications.length}<button
						onclick={() => runtime.dispatch('notifications.clear')}>Clear all</button
					>{/if}
			</div>
			<div class="notifications">
				{#each $osState.notifications as notification (notification.id)}<article
						class:unread={notification.unread}
					>
						<i>{notification.app[0]}</i>
						<div>
							<strong>{notification.title}</strong>
							<p>{notification.body}</p>
							<small>{notification.app} · {notification.time}</small>
						</div>
						<button
							aria-label={`Dismiss ${notification.title}`}
							onclick={() =>
								runtime.dispatch({ node: 'notifications.dismiss', input: notification.id })}
							>×</button
						>
					</article>{/each}{#if !$osState.notifications.length}<p class="empty-state">
						You're all caught up.
					</p>{/if}
			</div>
		</section>
	{/if}

	{#if $osState.overlay === 'clipboard'}
		<section class="small-popover clipboard-popover" aria-label="Clipboard history">
			<header>
				<div>
					<p class="eyebrow">CLIPBOARD</p>
					<h2>Recent copies</h2>
				</div>
				<span>Super V</span>
			</header>
			{#each $osState.clipboard as item, index (item)}<button
					onclick={() => runtime.dispatch({ node: 'clipboard.copy', input: item })}
					><small>{index === 0 ? 'CURRENT' : `${index + 1}`}</small><span>{item}</span><b>Copy</b
					></button
				>{/each}
			<footer>
				<button onclick={() => runtime.dispatch({ node: 'clipboard.copy', input: 'Pinned note' })}
					>＋ Add pinned note</button
				>
			</footer>
		</section>
	{/if}

	{#if $osState.overlay === 'capture'}
		<section class="capture-bar" aria-label="Screen capture">
			<div><button class="active">Screenshot</button><button>Record</button></div>
			<span></span>{#each ['Full screen', 'Window', 'Selection'] as mode (mode)}<button
					onclick={() => runtime.dispatch({ node: 'capture.save', input: mode })}
					>{mode === 'Full screen' ? '▣' : mode === 'Window' ? '▤' : '⌗'}<small>{mode}</small
					></button
				>{/each}<span></span><button
				class="capture-action"
				onclick={() => runtime.dispatch({ node: 'capture.save', input: 'Screenshot' })}
				>Capture</button
			>
		</section>
	{/if}

	{#if $osState.overlay === 'power'}
		<section class="power-menu" aria-label="Power menu">
			<div class="avatar">A</div>
			<h2>Researcher</h2>
			<p>What would you like to do?</p>
			<div>
				{#each [['↶', 'Log Out'], ['▣', 'Lock'], ['↻', 'Restart'], ['⏻', 'Power Off']] as action (action[1])}<button
						onclick={() => runtime.dispatch('panel.power')}><i>{action[0]}</i>{action[1]}</button
					>{/each}
			</div>
			<button onclick={() => runtime.dispatch('panel.power')}>Cancel</button>
		</section>
	{/if}

	{#if $osState.toast}<div class="toast" role="status">✓ {$osState.toast}</div>{/if}

	{#if $osState.menuOpen}
		<section class="app-menu" aria-label="Application menu">
			<label class="menu-search"
				><img src="/assets/icons/search.svg" alt="" /><input
					aria-label="Search applications"
					placeholder="Search applications"
					value={$osState.menuSearch}
					oninput={(event) =>
						runtime.dispatch({ node: 'menu.search', input: event.currentTarget.value })}
				/></label
			>
			<div class="menu-profile">
				<div class="avatar">A</div>
				<div><strong>Researcher</strong><span>AgentOS session</span></div>
			</div>
			<div class="app-list">
				{#each filteredApplications as app (app.id)}<button onclick={() => runtime.dispatch(app.id)}
						><img src={app.icon} alt="" /><span
							><strong>{app.label}</strong><small>{app.note}</small></span
						></button
					>{/each}
			</div>
			<footer>
				<button onclick={() => runtime.dispatch('panel.power')}
					><img src="/assets/icons/power.svg" alt="" /> Power</button
				>
			</footer>
		</section>
	{/if}

	{#if $osState.wifiOpen}
		<section class="wifi-panel" aria-label="Wi-Fi controls">
			<header>
				<strong>Wi-Fi</strong><button
					class:enabled={$osState.wifiEnabled}
					class="switch"
					onclick={() => runtime.dispatch('wifi.toggle')}
					aria-label="Toggle Wi-Fi"><span></span></button
				>
			</header>
			{#if $osState.wifiEnabled}
				{#each [{ id: 'wifi.studionet.connect', name: 'StudioNet', strength: 'Excellent' }, { id: 'wifi.pinehouse.connect', name: 'PineHouse', strength: 'Good' }] as network (network.id)}<button
						class:connected={$osState.connectedNetwork === network.name}
						class="network-row"
						onclick={() => runtime.dispatch(network.id)}
						><img src="/assets/icons/wifi.svg" alt="" /><span
							><strong>{network.name}</strong><small
								>{$osState.connectedNetwork === network.name
									? 'Connected'
									: network.strength}</small
							></span
						></button
					>{/each}
			{:else}<p class="wifi-off">Wireless networking is disabled</p>{/if}
			<button class="settings-link" onclick={() => runtime.dispatch('panel.inspector')}
				>Network settings…</button
			>
		</section>
	{/if}

	<nav class="panel" aria-label="System panel">
		<div class="panel-left">
			<button
				class:active={$osState.overlay === 'launcher'}
				class="launcher"
				onclick={() => runtime.dispatch('panel.menu')}
				aria-label="Applications"><img src="/assets/icons/menu.svg" alt="" /></button
			><button class="pinned" onclick={() => runtime.dispatch('panel.files')} aria-label="Files"
				><img src="/assets/icons/folder.svg" alt="" /></button
			><button
				class="pinned"
				onclick={() => runtime.dispatch('menu.terminal.open')}
				aria-label="Terminal"><img src="/assets/icons/terminal.svg" alt="" /></button
			>
			<button
				class:active={$osState.overlay === 'overview'}
				class="workspace-button"
				onclick={() => runtime.dispatch('panel.overview')}
				aria-label="Overview"><span>{$osState.workspace}</span><small>Workspace</small></button
			>
			<button
				class:active={$osState.focusedWindow === 'editor'}
				class="task-button"
				onclick={() => runtime.dispatch('panel.editor')}
				><img src="/assets/icons/editor.svg" alt="" /><span>desktop-actions-notes.txt</span></button
			><button
				class:active={$osState.focusedWindow === 'inspector'}
				class="task-button inspector-task"
				onclick={() => runtime.dispatch('panel.inspector')}
				><img src="/assets/icons/settings.svg" alt="" /><span>Control Graph Inspector</span></button
			>
		</div>
		<div class="panel-right">
			<button
				class:active={$osState.overlay === 'clipboard'}
				onclick={() => runtime.dispatch('panel.clipboard')}
				aria-label="Clipboard history"><span class="panel-glyph">▣</span></button
			>
			<button
				class:active={$osState.overlay === 'capture'}
				onclick={() => runtime.dispatch('panel.capture')}
				aria-label="Screen capture"><span class="panel-glyph">⌗</span></button
			>
			<button
				class:active={$osState.wifiOpen}
				onclick={() => runtime.dispatch('panel.network')}
				aria-label="Network"><img src="/assets/icons/wifi.svg" alt="" /></button
			><button
				onclick={() => runtime.dispatch('panel.control')}
				aria-label={`Volume ${$osState.volume}%`}
				><img src="/assets/icons/volume.svg" alt="" /></button
			><img class="tray-icon" src="/assets/icons/battery.svg" alt="Battery 80%" /><span
				class="battery-label">80%</span
			><button class="clock" onclick={() => console.info('AgentOS clock', clock)}
				><span
					>{new Intl.DateTimeFormat('en-GB', {
						hour: '2-digit',
						minute: '2-digit',
						hour12: false
					}).format(clock)}</span
				><small
					>{new Intl.DateTimeFormat('en-US', {
						weekday: 'short',
						month: 'short',
						day: 'numeric'
					}).format(clock)}</small
				></button
			>
		</div>
	</nav>
</main>
