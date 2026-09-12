<script lang="ts">
	import { onMount } from 'svelte';
	import { createOSRuntime } from '$lib/os/runtime';
	import type { OSCommand } from '$lib/os/types';

	const runtime = createOSRuntime();
	const osState = runtime.state;
	const osEvents = runtime.events;
	let invokeValue = $state('panel.network');
	let clock = $state(new Date());

	const desktopIcons = [
		{ id: 'desktop.home', label: 'Home', icon: '/assets/icons/home.svg' },
		{ id: 'desktop.trash', label: 'Trash', icon: '/assets/icons/trash.svg' },
		{ id: 'desktop.filesystem', label: 'File System', icon: '/assets/icons/drive.svg' },
		{ id: 'desktop.research', label: 'Research', icon: '/assets/icons/folder.svg' }
	];

	const applications = [
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
		}
	];

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
			window.removeEventListener('agentos:command', receiveCommand);
			window.removeEventListener('message', receiveMessage);
		};
	});

	function beginDrag(event: PointerEvent, name: 'editor' | 'inspector' | 'files') {
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

	function windowStyle(name: 'editor' | 'inspector' | 'files'): string {
		const current = $osState.windows[name];
		return current.maximized
			? `z-index:${current.z}`
			: `left:${current.x}px;top:${current.y}px;z-index:${current.z}`;
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
</script>

<svelte:head
	><title>AgentOS Research Desktop</title><meta
		name="description"
		content="A graph-native simulated desktop environment"
	/></svelte:head
>

<main class="desktop" aria-label="AgentOS desktop">
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

	{#if $osState.windows.editor.open && !$osState.windows.editor.minimized}
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
					desktop-actions-notes.txt <span>— ~/Documents/Research</span>
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
				><button title="Save document"><img src="/assets/icons/document-save.svg" alt="" /></button
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

	{#if $osState.windows.inspector.open && !$osState.windows.inspector.minimized}
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

	{#if $osState.windows.files.open && !$osState.windows.files.minimized}
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
			</div>
			<div class="files-body">
				<aside>
					<strong>Places</strong><button>Home</button><button>Desktop</button><button
						>Documents</button
					><button>Downloads</button><button>Trash</button>
				</aside>
				<div class="folder-grid">
					{#each ['Desktop', 'Documents', 'Downloads', 'Pictures', 'Music', 'Research'] as folder (folder)}<button
							><img src="/assets/icons/folder.svg" alt="" /><span>{folder}</span></button
						>{/each}
				</div>
			</div>
		</section>
	{/if}

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
				class:active={$osState.menuOpen}
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
				class:active={$osState.wifiOpen}
				onclick={() => runtime.dispatch('panel.network')}
				aria-label="Network"><img src="/assets/icons/wifi.svg" alt="" /></button
			><button
				onclick={() => runtime.dispatch('panel.sound')}
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
