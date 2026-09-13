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

export interface DesktopObservedState {
	environment_version: string;
	revision: number;
	fields: {
		wifi: {
			enabled: boolean;
			ssid: string | null;
		};
		task: {
			last_failure: {
				action: string;
				code: string;
				recoverable: boolean;
			} | null;
		};
		[domain: string]: unknown;
	};
	unknown_fields: string[];
}

export type AgentObservedState = WifiObservedState | DesktopObservedState;

export interface AgentTaskResult {
	command: string;
	goal:
		| {
				type: 'wifi_enabled' | 'wifi_disabled' | 'connected' | 'disconnected';
				ssid: string | null;
		  }
		| { id: string; milestones: unknown[]; constraints: Record<string, unknown> };
	route: 'deterministic' | 'q_learning';
	plan: Array<{ action: string; args: Record<string, unknown> }>;
	executions: Array<{
		action: string;
		args: Record<string, unknown>;
		status: 'succeeded' | 'failed' | 'cancelled' | 'confirmation_required';
		message: string;
		observed_state: AgentObservedState;
	}>;
	status: 'succeeded' | 'failed' | 'cancelled' | 'confirmation_required';
	final_state: AgentObservedState;
	error: string | null;
	training?: {
		policy_version: string;
		cache_key: string;
		episodes: number;
		states: number;
		action_space: number;
		success_rate: number;
		recent_traces: unknown[];
	};
	baselines?: {
		bfs: { steps: number | null; duration_ms: number };
		astar: { steps: number | null; duration_ms: number };
	};
	recovery?: {
		injected_failures: Record<string, number>;
		observed_failures: number;
		replans: number;
	};
	timeline?: LoopEvent[];
	duration_ms?: number;
}

export interface LoopEvent {
	sequence: number;
	phase: 'observe' | 'propose' | 'validate' | 'act' | 'verify' | 'recover';
	action: string | null;
	state_hash: string | null;
	status: string;
	detail: string;
}

export interface ActionSpec {
	id: string;
	description: string;
	arguments: Record<string, { type: string; required: boolean; description: string }>;
	preconditions: Array<{ field: string; operator: string; value: unknown }>;
	postconditions: Array<{ field: string; operator: string; value: unknown }>;
	effects: Array<{ field: string; operation: string; value: unknown }>;
	cost: number;
	latency: string;
	risk: 'low' | 'medium' | 'high';
	reversible: boolean;
	confirmation_required: boolean;
}

export interface TaskPreview {
	source: string;
	expression: { operator: string; arguments?: unknown[]; text?: string };
	parameters: Record<string, unknown>;
	supported: boolean;
	task_id: string | null;
	milestones: Array<{
		id: string;
		description: string;
		mode: 'all' | 'any';
		goals: Array<{ id: string; predicate: { field: string; operator: string; value: unknown } }>;
	}>;
	constraints: Record<string, unknown>;
}

export interface AgentMetrics {
	tasks: number;
	success_rate: number;
	training_time_ms: number;
	inference_time_ms: number;
	environment_steps: number;
	unnecessary_actions: number;
	recovery_rate: number;
	policy_cache_hit_rate: number;
	planner_vs_rl: { bfs_steps: number; astar_steps: number; rl_steps: number };
	live_simulator_divergence: number;
	llm_escalation_frequency: number;
	llm_cost: number;
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
	copyFile(id: number, parentPath: string): Promise<FileEntry> {
		return request(`/files/${id}/copy`, {
			method: 'POST',
			body: JSON.stringify({ parent_path: parentPath })
		});
	},
	deleteFilePermanently(id: number): Promise<void> {
		return request(`/files/${id}/permanent`, { method: 'DELETE' });
	},
	emptyTrash(): Promise<{ deleted: number }> {
		return request('/files/trash/all', { method: 'DELETE' });
	},
	createArchive(nodeIds: number[], parentPath: string, name: string): Promise<FileEntry> {
		return request('/files/archive', {
			method: 'POST',
			body: JSON.stringify({ node_ids: nodeIds, parent_path: parentPath, name })
		});
	},
	extractArchive(id: number, destination: string): Promise<{ items: FileEntry[] }> {
		return request(`/files/${id}/extract`, {
			method: 'POST',
			body: JSON.stringify({ destination })
		});
	},
	commandStream(): EventSource {
		return new EventSource(`${API_BASE}/control`);
	},
	sendCommand(command: OSCommand): Promise<unknown> {
		return request('/control', { method: 'POST', body: JSON.stringify(command) });
	},
	runAgentTask(command: string, signal?: AbortSignal): Promise<AgentTaskResult> {
		return request('/agent/tasks', { method: 'POST', body: JSON.stringify({ command }), signal });
	},
	previewTask(command: string): Promise<TaskPreview> {
		return request('/agent/preview', { method: 'POST', body: JSON.stringify({ command }) });
	},
	async loadActions(): Promise<ActionSpec[]> {
		return (await request<{ items: ActionSpec[] }>('/actions')).items;
	},
	executeAction(
		actionId: string,
		args: Record<string, unknown> = {},
		confirmed = false
	): Promise<Record<string, unknown>> {
		return request(`/actions/${encodeURIComponent(actionId)}/execute`, {
			method: 'POST',
			body: JSON.stringify({ args, confirmed })
		});
	},
	loadMetrics(): Promise<AgentMetrics> {
		return request('/agent/metrics');
	},
	async listPolicies(): Promise<Array<Record<string, unknown>>> {
		return (await request<{ items: Array<Record<string, unknown>> }>('/agent/policies')).items;
	},
	loadPolicy(cacheKey: string): Promise<Record<string, unknown>> {
		return request(`/agent/policies/${encodeURIComponent(cacheKey)}`);
	},
	cancelTask(taskId: string): Promise<unknown> {
		return request(`/agent/tasks/${encodeURIComponent(taskId)}/cancel`, { method: 'POST' });
	},
	rollbackTask(taskId: string): Promise<unknown> {
		return request(`/agent/tasks/${encodeURIComponent(taskId)}/rollback`, { method: 'POST' });
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
