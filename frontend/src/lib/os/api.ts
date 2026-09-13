import type { ActionEvent, OSCommand, OSState } from './types';

export const API_BASE = (import.meta.env.VITE_AGENTOS_API_URL ?? '/backend-api').replace(/\/$/, '');

export interface FileEntry {
	id: number;
	parent_id: number | null;
	name: string;
	kind: 'folder' | 'text' | 'file' | 'pdf' | 'archive' | 'image';
	mime_type: string | null;
	size: number;
	starred: boolean;
	deleted: boolean;
	created_at: string;
	updated_at: string;
	path: string;
	content?: string;
}

export interface WifiObservedState {
	enabled: boolean;
	connected: boolean;
	ssid: string | null;
	known_networks: string[];
	visible_networks: Array<{ ssid: string; signal_strength: number; known: boolean }>;
	internet_available: boolean;
}

export interface AgentTaskResult {
	command: string;
	goal: { type: 'wifi_enabled' | 'wifi_disabled' | 'connected' | 'disconnected'; ssid: string | null };
	route: 'deterministic';
	plan: Array<{ action: string; args: Record<string, unknown> }>;
	executions: Array<{
		action: string;
		args: Record<string, unknown>;
		status: 'succeeded' | 'failed';
		message: string;
		observed_state: WifiObservedState;
	}>;
	status: 'succeeded' | 'failed';
	final_state: WifiObservedState;
	error: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${API_BASE}${path}`, {
		...init,
		headers: { 'content-type': 'application/json', ...init?.headers }
	});
	if (!response.ok) {
		const body = await response.json().catch(() => ({ detail: response.statusText }));
		const detail = body.detail;
		throw new Error(
			typeof detail === 'string'
				? detail
				: typeof detail?.message === 'string'
					? detail.message
					: JSON.stringify(detail)
		);
	}
	return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export const osApi = {
	async loadState(): Promise<Partial<OSState>> {
		return (await request<{ value: Partial<OSState> }>('/state')).value;
	},
	saveState(value: OSState): Promise<{ revision: number }> {
		return request('/state', { method: 'PUT', body: JSON.stringify({ value }) });
	},
	async loadEvents(): Promise<ActionEvent[]> {
		return (await request<{ items: ActionEvent[] }>('/events')).items;
	},
	logEvent(event: ActionEvent, input?: unknown): Promise<unknown> {
		return request('/events', { method: 'POST', body: JSON.stringify({ ...event, input }) });
	},
	async listFiles(path: string, query = ''): Promise<FileEntry[]> {
		const params = new URLSearchParams({ path });
		if (query) params.set('query', query);
		return (await request<{ items: FileEntry[] }>(`/files?${params}`)).items;
	},
	async searchFiles(query: string): Promise<FileEntry[]> {
		return (await request<{ items: FileEntry[] }>(`/files/search?q=${encodeURIComponent(query)}`))
			.items;
	},
	createFile(value: {
		parent_path: string;
		name: string;
		kind: FileEntry['kind'];
		content?: string;
	}): Promise<FileEntry> {
		return request('/files', { method: 'POST', body: JSON.stringify(value) });
	},
	getFile(id: number, includeContent = false): Promise<FileEntry> {
		return request(`/files/${id}?include_content=${includeContent}`);
	},
	updateFile(
		id: number,
		value: { name?: string; parent_path?: string; starred?: boolean }
	): Promise<FileEntry> {
		return request(`/files/${id}`, { method: 'PATCH', body: JSON.stringify(value) });
	},
	saveFile(id: number, content: string): Promise<FileEntry> {
		return request(`/files/${id}/content`, {
			method: 'PUT',
			body: JSON.stringify({ content, mime_type: 'text/plain' })
		});
	},
	trashFile(id: number): Promise<void> {
		return request(`/files/${id}`, { method: 'DELETE' });
	},
	restoreFile(id: number): Promise<FileEntry> {
		return request(`/files/${id}/restore`, { method: 'POST' });
	},
	commandStream(): EventSource {
		return new EventSource(`${API_BASE}/control`);
	},
	sendCommand(command: OSCommand): Promise<unknown> {
		return request('/control', { method: 'POST', body: JSON.stringify(command) });
	},
	runAgentTask(command: string): Promise<AgentTaskResult> {
		return request('/agent/tasks', { method: 'POST', body: JSON.stringify({ command }) });
	}
};

export function formatFileMeta(file: FileEntry): string {
	if (file.kind === 'folder') return 'Folder';
	const units = ['B', 'KB', 'MB', 'GB'];
	let size = file.size;
	let unit = 0;
	while (size >= 1024 && unit < units.length - 1) {
		size /= 1024;
		unit += 1;
	}
	return `${unit === 0 ? size : size.toFixed(1)} ${units[unit]}`;
}
