import type { OSCommand, OSState } from './types';

export const taskActionSpace = [
	'clipboard.read',
	'window.editor.new',
	'window.editor.paste',
	'window.editor.save',
	'panel.clipboard',
	'menu.editor.open'
] as const;

type TaskAction = (typeof taskActionSpace)[number];
const findAppendActionSpace = [
	'filesystem.search',
	'filesystem.open_file',
	'clipboard.read',
	'editor.insert',
	'editor.save',
	'panel.clipboard',
	'menu.editor.open'
] as const;
type FindAppendAction = (typeof findAppendActionSpace)[number];
const organizeNoteActionSpace = [
	'filesystem.open',
	'filesystem.create_folder',
	'clipboard.read',
	'editor.new_document',
	'editor.paste_content',
	'editor.save_as',
	'panel.clipboard',
	'menu.editor.open'
] as const;
type OrganizeNoteAction = (typeof organizeNoteActionSpace)[number];
const researchHandoffActionSpace = [
	'browser.focus',
	'browser.copy_url',
	'editor.new_document',
	'editor.paste_content',
	'editor.save_as',
	'filesystem.search',
	'filesystem.reveal'
] as const;
type ResearchHandoffAction = (typeof researchHandoffActionSpace)[number];
const workspaceSetupActionSpace = [
	'workspace.create',
	'workspace.switch',
	'browser.open',
	'editor.open',
	'window.snap',
	'editor.new_document',
	'editor.paste_content',
	'editor.save_as',
	'panel.overview',
	'workspace.window.move'
] as const;
type WorkspaceSetupAction = (typeof workspaceSetupActionSpace)[number];
const downloadArchiveActionSpace = [
	'browser.open',
	'browser.download',
	'filesystem.open_downloads',
	'filesystem.search',
	'filesystem.rename',
	'filesystem.create_folder',
	'filesystem.move',
	'filesystem.compress',
	'filesystem.open',
	'panel.clipboard',
	'menu.editor.open'
] as const;
type DownloadArchiveAction = (typeof downloadArchiveActionSpace)[number];
const clipboardReportActionSpace = [
	'clipboard.read',
	'filesystem.create_folder',
	'editor.new_document',
	'editor.paste_content',
	'editor.save_as',
	'editor.close_document',
	'filesystem.open',
	'filesystem.search',
	'filesystem.move',
	'filesystem.star',
	'panel.clipboard',
	'menu.editor.open'
] as const;
type ClipboardReportAction = (typeof clipboardReportActionSpace)[number];
type LearnedAction =
	| TaskAction
	| FindAppendAction
	| OrganizeNoteAction
	| ResearchHandoffAction
	| WorkspaceSetupAction
	| DownloadArchiveAction
	| ClipboardReportAction;
type TaskMilestone =
	| 'clipboard_captured'
	| 'empty_document_created'
	| 'clipboard_content_pasted'
	| 'document_saved_with_name';

export interface ClipboardFileIntent {
	type: 'clipboard_to_text_file';
	filename: string;
}

export interface FindAppendIntent {
	type: 'find_and_append';
	filename: string;
}

export interface OrganizeNoteIntent {
	type: 'organize_note';
	parent: string;
	folder: string;
	filename: string;
}

export interface ResearchHandoffIntent {
	type: 'research_handoff';
	filename: string;
}

export interface WorkspaceSetupIntent {
	type: 'workspace_setup';
	workspace: number;
	filename: string;
}

export interface DownloadArchiveIntent {
	type: 'download_and_archive';
	filename: string;
	folder: string;
}

export interface ClipboardReportIntent {
	type: 'clipboard_report';
	parent: string;
	folder: string;
	filename: string;
}

export interface CompiledTask {
	goal: ClipboardFileIntent;
	milestones: TaskMilestone[];
}

interface TrainingState {
	progress: number;
	clipboardCaptured: boolean;
	documentCreated: boolean;
	contentPasted: boolean;
	savedName: string | null;
}

export interface LearnedTaskResult {
	command: string;
	goal:
		| ClipboardFileIntent
		| FindAppendIntent
		| OrganizeNoteIntent
		| ResearchHandoffIntent
		| WorkspaceSetupIntent
		| DownloadArchiveIntent
		| ClipboardReportIntent;
	route: 'q_learning';
	training: { episodes: number; states: number; actions: number };
	plan: Array<{ action: LearnedAction }>;
	executions: Array<{
		action: LearnedAction;
		status: 'succeeded' | 'failed';
		message: string;
	}>;
	status: 'succeeded' | 'failed';
	error: string | null;
}

interface FindAppendState {
	progress: number;
	searched: boolean;
	opened: boolean;
	clipboardCaptured: boolean;
	contentInserted: boolean;
	saved: boolean;
}

interface OrganizeNoteState {
	progress: number;
	parentOpened: boolean;
	folderCreated: boolean;
	clipboardCaptured: boolean;
	documentCreated: boolean;
	contentPasted: boolean;
	savedInFolder: boolean;
}

interface ResearchHandoffState {
	progress: number;
	browserFocused: boolean;
	addressCopied: boolean;
	documentCreated: boolean;
	addressPasted: boolean;
	documentSaved: boolean;
	fileFound: boolean;
	fileRevealed: boolean;
}

interface WorkspaceSetupState {
	progress: number;
	workspaceCreated: boolean;
	workspaceSelected: boolean;
	browserOpened: boolean;
	editorOpened: boolean;
	windowsArranged: boolean;
	documentCreated: boolean;
	contentPasted: boolean;
	documentSaved: boolean;
}

interface DownloadArchiveState {
	progress: number;
	browserOpened: boolean;
	pageDownloaded: boolean;
	downloadsOpened: boolean;
	downloadFound: boolean;
	downloadRenamed: boolean;
	folderCreated: boolean;
	downloadMoved: boolean;
	archiveCreated: boolean;
	archiveLocationOpened: boolean;
}

interface ClipboardReportState {
	progress: number;
	clipboardCaptured: boolean;
	folderCreated: boolean;
	documentCreated: boolean;
	contentPasted: boolean;
	documentSaved: boolean;
	documentClosed: boolean;
	filesOpened: boolean;
	fileFound: boolean;
	fileMoved: boolean;
	fileStarred: boolean;
}

export interface TaskRuntime {
	dispatch(
		command: OSCommand,
		source?: 'human' | 'remote' | 'system'
	): Promise<{ result: 'ok' | 'error'; detail: string }>;
	snapshot(): Pick<
		OSState,
		'clipboard' | 'editorText' | 'filesPath' | 'workspace' | 'workspaceCount' | 'windows'
	>;
}

export function compileClipboardFileIntent(command: string): CompiledTask | null {
	const normalized = command.trim().replace(/\s+/g, ' ');
	const lowered = normalized.toLowerCase();
	if (
		!lowered.includes('clipboard') ||
		!/(?:new|create|make) (?:a )?(?:new )?(?:text )?(?:file|document)/i.test(normalized) ||
		!lowered.includes('paste') ||
		!lowered.includes('save')
	)
		return null;

	const quotedName = normalized.match(
		/\bsave(?:\s+it)?\s+(?:with\s+(?:the\s+)?name|as)\s+["']([^"']+)["']/i
	)?.[1];
	const plainName = normalized.match(
		/\bsave(?:\s+it)?\s+(?:with\s+(?:the\s+)?name|as)\s+([\w.-]+)\s*[.!]?$/i
	)?.[1];
	const filename = (quotedName ?? plainName)?.trim();
	return filename
		? {
				goal: { type: 'clipboard_to_text_file', filename },
				milestones: [
					'clipboard_captured',
					'empty_document_created',
					'clipboard_content_pasted',
					'document_saved_with_name'
				]
			}
		: null;
}

function applyTrainingAction(
	state: TrainingState,
	action: TaskAction,
	filename: string
): TrainingState {
	const next = { ...state };
	if (action === 'clipboard.read') next.clipboardCaptured = true;
	if (action === 'window.editor.new') {
		next.documentCreated = true;
		next.contentPasted = false;
		next.savedName = null;
	}
	if (action === 'window.editor.paste' && state.clipboardCaptured && state.documentCreated)
		next.contentPasted = true;
	if (action === 'window.editor.save' && state.documentCreated && state.contentPasted)
		next.savedName = filename;
	return next;
}

function milestoneSatisfied(
	milestone: TaskMilestone,
	state: TrainingState,
	filename: string
): boolean {
	if (milestone === 'clipboard_captured') return state.clipboardCaptured;
	if (milestone === 'empty_document_created') return state.documentCreated && !state.contentPasted;
	if (milestone === 'clipboard_content_pasted') return state.contentPasted;
	return state.savedName === filename;
}

function transition(
	state: TrainingState,
	action: TaskAction,
	task: CompiledTask
): { state: TrainingState; reward: number } {
	const milestone = task.milestones[state.progress];
	const wasSatisfied = milestone ? milestoneSatisfied(milestone, state, task.goal.filename) : true;
	const next = applyTrainingAction(state, action, task.goal.filename);
	if (!milestone || wasSatisfied || !milestoneSatisfied(milestone, next, task.goal.filename))
		return { state: next, reward: -2 };
	next.progress += 1;
	return { state: next, reward: next.progress === task.milestones.length ? 20 : 3 };
}

function seededRandom() {
	let seed = 0x5eed1234;
	return () => {
		seed = (1664525 * seed + 1013904223) >>> 0;
		return seed / 0x100000000;
	};
}

function bestAction(qValues: number[]): number {
	return qValues.reduce((best, value, index) => (value > qValues[best] ? index : best), 0);
}

function stateKey(state: TrainingState): string {
	return [
		state.progress,
		Number(state.clipboardCaptured),
		Number(state.documentCreated),
		Number(state.contentPasted),
		Number(state.savedName !== null)
	].join(':');
}

function qValues(qTable: Map<string, number[]>, state: TrainingState): number[] {
	const key = stateKey(state);
	let values = qTable.get(key);
	if (!values) {
		values = taskActionSpace.map(() => 0);
		qTable.set(key, values);
	}
	return values;
}

export interface TrainedPolicy {
	actions: TaskAction[];
	statesVisited: number;
}

export function trainTaskPolicy(task: CompiledTask, episodes = 1200): TrainedPolicy {
	const qTable = new Map<string, number[]>();
	const random = seededRandom();
	const alpha = 0.25;
	const gamma = 0.9;

	for (let episode = 0; episode < episodes; episode += 1) {
		let state: TrainingState = {
			progress: 0,
			clipboardCaptured: false,
			documentCreated: false,
			contentPasted: false,
			savedName: null
		};
		const epsilon = Math.max(0.05, 0.9 * (1 - episode / episodes));
		for (let step = 0; step < 24 && state.progress !== task.milestones.length; step += 1) {
			const actionIndex =
				random() < epsilon
					? Math.floor(random() * taskActionSpace.length)
					: bestAction(qValues(qTable, state));
			const outcome = transition(state, taskActionSpace[actionIndex], task);
			const future =
				outcome.state.progress === task.milestones.length
					? 0
					: Math.max(...qValues(qTable, outcome.state));
			const values = qValues(qTable, state);
			values[actionIndex] += alpha * (outcome.reward - 0.05 + gamma * future - values[actionIndex]);
			state = outcome.state;
		}
	}

	const policy: TaskAction[] = [];
	let state: TrainingState = {
		progress: 0,
		clipboardCaptured: false,
		documentCreated: false,
		contentPasted: false,
		savedName: null
	};
	while (state.progress !== task.milestones.length) {
		const action = taskActionSpace[bestAction(qValues(qTable, state))];
		const outcome = transition(state, action, task);
		if (outcome.state.progress === state.progress)
			throw new Error('Learned policy did not converge');
		policy.push(action);
		state = outcome.state;
	}
	return { actions: policy, statesVisited: qTable.size };
}

export async function runClipboardFileTask(
	runtime: TaskRuntime,
	command: string
): Promise<LearnedTaskResult | null> {
	const task = compileClipboardFileIntent(command);
	if (!task) return null;
	const clipboardContent = runtime.snapshot().clipboard[0];
	if (clipboardContent === undefined) throw new Error('The clipboard is empty');

	const policy = trainTaskPolicy(task);
	const { actions } = policy;
	const executions: LearnedTaskResult['executions'] = [];
	for (const action of actions) {
		const input =
			action === 'clipboard.read' || action === 'window.editor.paste'
				? clipboardContent
				: action === 'window.editor.save'
					? task.goal.filename
					: undefined;
		const event = await runtime.dispatch({ node: action, input }, 'system');
		executions.push({
			action,
			status: event.result === 'ok' ? 'succeeded' : 'failed',
			message: event.detail
		});
		if (event.result === 'error')
			return buildResult(command, task, policy, executions, 'failed', event.detail);
	}

	const pasted = runtime.snapshot().editorText === clipboardContent;
	return buildResult(
		command,
		task,
		policy,
		executions,
		pasted ? 'succeeded' : 'failed',
		pasted ? null : 'The final editor content does not match the clipboard'
	);
}

export function compileFindAppendIntent(command: string): FindAppendIntent | null {
	const normalized = command.trim().replace(/\s+/g, ' ');
	if (
		!/\bfind\b/i.test(normalized) ||
		!/\b(?:append|add)\b/i.test(normalized) ||
		!normalized.toLowerCase().includes('clipboard') ||
		!/\bsave\b/i.test(normalized)
	)
		return null;
	const filename = normalized.match(/\bfile\s+(?:named|called)\s+["']?([\w.-]+)["']?/i)?.[1];
	return filename ? { type: 'find_and_append', filename } : null;
}

function applyFindAppendAction(state: FindAppendState, action: FindAppendAction): FindAppendState {
	const next = { ...state };
	if (action === 'filesystem.search') next.searched = true;
	if (action === 'filesystem.open_file' && state.searched) next.opened = true;
	if (action === 'clipboard.read' && state.opened) next.clipboardCaptured = true;
	if (action === 'editor.insert' && state.opened && state.clipboardCaptured)
		next.contentInserted = true;
	if (action === 'editor.save' && state.contentInserted) next.saved = true;
	return next;
}

function findAppendMilestoneSatisfied(progress: number, state: FindAppendState): boolean {
	if (progress === 0) return state.searched;
	if (progress === 1) return state.opened;
	if (progress === 2) return state.clipboardCaptured;
	if (progress === 3) return state.contentInserted;
	return state.saved;
}

function findAppendTransition(
	state: FindAppendState,
	action: FindAppendAction
): { state: FindAppendState; reward: number } {
	const next = applyFindAppendAction(state, action);
	if (!findAppendMilestoneSatisfied(state.progress, next)) return { state: next, reward: -2 };
	next.progress += 1;
	return { state: next, reward: next.progress === 5 ? 20 : 3 };
}

function findAppendStateKey(state: FindAppendState): string {
	return [
		state.progress,
		Number(state.searched),
		Number(state.opened),
		Number(state.clipboardCaptured),
		Number(state.contentInserted),
		Number(state.saved)
	].join(':');
}

function trainFindAppendPolicy(episodes = 1600): {
	actions: FindAppendAction[];
	statesVisited: number;
} {
	const qTable = new Map<string, number[]>();
	const random = seededRandom();
	const valuesFor = (state: FindAppendState) => {
		const key = findAppendStateKey(state);
		let values = qTable.get(key);
		if (!values) {
			values = findAppendActionSpace.map(() => 0);
			qTable.set(key, values);
		}
		return values;
	};
	const initialState = (): FindAppendState => ({
		progress: 0,
		searched: false,
		opened: false,
		clipboardCaptured: false,
		contentInserted: false,
		saved: false
	});
	for (let episode = 0; episode < episodes; episode += 1) {
		let state = initialState();
		const epsilon = Math.max(0.05, 0.9 * (1 - episode / episodes));
		for (let step = 0; step < 32 && state.progress !== 5; step += 1) {
			const values = valuesFor(state);
			const actionIndex =
				random() < epsilon
					? Math.floor(random() * findAppendActionSpace.length)
					: bestAction(values);
			const outcome = findAppendTransition(state, findAppendActionSpace[actionIndex]);
			const future = outcome.state.progress === 5 ? 0 : Math.max(...valuesFor(outcome.state));
			values[actionIndex] += 0.25 * (outcome.reward - 0.05 + 0.9 * future - values[actionIndex]);
			state = outcome.state;
		}
	}
	const actions: FindAppendAction[] = [];
	let state = initialState();
	while (state.progress !== 5) {
		const action = findAppendActionSpace[bestAction(valuesFor(state))];
		const outcome = findAppendTransition(state, action);
		if (outcome.state.progress === state.progress)
			throw new Error('Learned policy did not converge');
		actions.push(action);
		state = outcome.state;
	}
	return { actions, statesVisited: qTable.size };
}

export async function runFindAppendTask(
	runtime: TaskRuntime,
	command: string
): Promise<LearnedTaskResult | null> {
	const goal = compileFindAppendIntent(command);
	if (!goal) return null;
	const clipboardContent = runtime.snapshot().clipboard[0];
	if (clipboardContent === undefined) throw new Error('The clipboard is empty');
	const policy = trainFindAppendPolicy();
	const executions: LearnedTaskResult['executions'] = [];
	for (const action of policy.actions) {
		const input =
			action === 'filesystem.search' || action === 'filesystem.open_file'
				? goal.filename
				: action === 'editor.insert'
					? { position: 'end', content: clipboardContent }
					: action === 'clipboard.read'
						? clipboardContent
						: undefined;
		const event = await runtime.dispatch({ node: action, input }, 'system');
		executions.push({
			action,
			status: event.result === 'ok' ? 'succeeded' : 'failed',
			message: event.detail
		});
		if (event.result === 'error')
			return buildFindAppendResult(command, goal, policy, executions, 'failed', event.detail);
	}
	return buildFindAppendResult(command, goal, policy, executions, 'succeeded', null);
}

export function compileOrganizeNoteIntent(command: string): OrganizeNoteIntent | null {
	const normalized = command.trim().replace(/\s+/g, ' ');
	if (
		!/\bcreate\b/i.test(normalized) ||
		!/\bfolder\b/i.test(normalized) ||
		!/(?:\bclipboard\b|\bnote from (?:the )?clipboard\b)/i.test(normalized) ||
		!/\bsave\b/i.test(normalized)
	)
		return null;
	const folderMatch = normalized.match(
		/\bcreate\s+(?:a\s+)?(?:folder\s+)?["']?([\w .-]+?)["']?\s+folder\s+in\s+["']?([\w /.-]+?)["']?(?=,|\bthen\b|\band\b)/i
	);
	const alternateFolderMatch = normalized.match(
		/\bcreate\s+(?:a\s+)?["']?([\w .-]+?)["']?\s+in\s+["']?([\w /.-]+?)["']?\s+folder\b/i
	);
	const filename = normalized.match(
		/\bsave(?:\s+it)?\s+(?:as|with\s+(?:the\s+)?name)\s+["']?([\w.-]+)["']?/i
	)?.[1];
	const match = folderMatch ?? alternateFolderMatch;
	if (!match || !filename) return null;
	return {
		type: 'organize_note',
		folder: match[1].trim(),
		parent: match[2].trim(),
		filename: filename.trim()
	};
}

function applyOrganizeNoteAction(
	state: OrganizeNoteState,
	action: OrganizeNoteAction
): OrganizeNoteState {
	const next = { ...state };
	if (action === 'filesystem.open') next.parentOpened = true;
	if (action === 'filesystem.create_folder' && state.parentOpened) next.folderCreated = true;
	if (action === 'clipboard.read' && state.folderCreated) next.clipboardCaptured = true;
	if (action === 'editor.new_document' && state.clipboardCaptured) next.documentCreated = true;
	if (action === 'editor.paste_content' && state.documentCreated) next.contentPasted = true;
	if (action === 'editor.save_as' && state.contentPasted && state.folderCreated)
		next.savedInFolder = true;
	return next;
}

function organizeNoteMilestoneSatisfied(progress: number, state: OrganizeNoteState): boolean {
	if (progress === 0) return state.parentOpened;
	if (progress === 1) return state.folderCreated;
	if (progress === 2) return state.clipboardCaptured;
	if (progress === 3) return state.documentCreated;
	if (progress === 4) return state.contentPasted;
	return state.savedInFolder;
}

function organizeNoteTransition(
	state: OrganizeNoteState,
	action: OrganizeNoteAction
): { state: OrganizeNoteState; reward: number } {
	const next = applyOrganizeNoteAction(state, action);
	if (!organizeNoteMilestoneSatisfied(state.progress, next)) return { state: next, reward: -2 };
	next.progress += 1;
	return { state: next, reward: next.progress === 6 ? 20 : 3 };
}

function trainOrganizeNotePolicy(episodes = 2200): {
	actions: OrganizeNoteAction[];
	statesVisited: number;
} {
	const qTable = new Map<string, number[]>();
	const random = seededRandom();
	const initialState = (): OrganizeNoteState => ({
		progress: 0,
		parentOpened: false,
		folderCreated: false,
		clipboardCaptured: false,
		documentCreated: false,
		contentPasted: false,
		savedInFolder: false
	});
	const valuesFor = (state: OrganizeNoteState) => {
		const key = [
			state.progress,
			Number(state.parentOpened),
			Number(state.folderCreated),
			Number(state.clipboardCaptured),
			Number(state.documentCreated),
			Number(state.contentPasted),
			Number(state.savedInFolder)
		].join(':');
		let values = qTable.get(key);
		if (!values) {
			values = organizeNoteActionSpace.map(() => 0);
			qTable.set(key, values);
		}
		return values;
	};
	for (let episode = 0; episode < episodes; episode += 1) {
		let state = initialState();
		const epsilon = Math.max(0.05, 0.9 * (1 - episode / episodes));
		for (let step = 0; step < 40 && state.progress !== 6; step += 1) {
			const values = valuesFor(state);
			const actionIndex =
				random() < epsilon
					? Math.floor(random() * organizeNoteActionSpace.length)
					: bestAction(values);
			const outcome = organizeNoteTransition(state, organizeNoteActionSpace[actionIndex]);
			const future = outcome.state.progress === 6 ? 0 : Math.max(...valuesFor(outcome.state));
			values[actionIndex] += 0.25 * (outcome.reward - 0.05 + 0.9 * future - values[actionIndex]);
			state = outcome.state;
		}
	}
	const actions: OrganizeNoteAction[] = [];
	let state = initialState();
	while (state.progress !== 6) {
		const action = organizeNoteActionSpace[bestAction(valuesFor(state))];
		const outcome = organizeNoteTransition(state, action);
		if (outcome.state.progress === state.progress)
			throw new Error('Learned policy did not converge');
		actions.push(action);
		state = outcome.state;
	}
	return { actions, statesVisited: qTable.size };
}

export async function runOrganizeNoteTask(
	runtime: TaskRuntime,
	command: string
): Promise<LearnedTaskResult | null> {
	const goal = compileOrganizeNoteIntent(command);
	if (!goal) return null;
	const clipboardContent = runtime.snapshot().clipboard[0];
	if (clipboardContent === undefined) throw new Error('The clipboard is empty');
	const policy = trainOrganizeNotePolicy();
	const executions: LearnedTaskResult['executions'] = [];
	for (const action of policy.actions) {
		const input =
			action === 'filesystem.open'
				? goal.parent
				: action === 'filesystem.create_folder'
					? { parent: goal.parent, name: goal.folder }
					: action === 'clipboard.read' || action === 'editor.paste_content'
						? clipboardContent
						: action === 'editor.save_as'
							? { name: goal.filename, parent: `${goal.parent}/${goal.folder}` }
							: undefined;
		const event = await runtime.dispatch({ node: action, input }, 'system');
		executions.push({
			action,
			status: event.result === 'ok' ? 'succeeded' : 'failed',
			message: event.detail
		});
		if (event.result === 'error')
			return buildOrganizeNoteResult(command, goal, policy, executions, 'failed', event.detail);
	}
	return buildOrganizeNoteResult(command, goal, policy, executions, 'succeeded', null);
}

export function compileResearchHandoffIntent(command: string): ResearchHandoffIntent | null {
	const normalized = command.trim().replace(/\s+/g, ' ');
	if (
		!/\bbrowser\b/i.test(normalized) ||
		!/\b(?:address|url)\b/i.test(normalized) ||
		!/\b(?:copy|capture)\b/i.test(normalized) ||
		!/\b(?:note|document|file)\b/i.test(normalized) ||
		!/\bpaste\b/i.test(normalized) ||
		!/\bsave\b/i.test(normalized) ||
		!/\breveal\b/i.test(normalized)
	)
		return null;
	const filename = normalized.match(
		/\bsave(?:\s+it)?\s+(?:as|with\s+(?:the\s+)?name)\s+["']?([\w.-]+)["']?/i
	)?.[1];
	return filename ? { type: 'research_handoff', filename: filename.trim() } : null;
}

function applyResearchHandoffAction(
	state: ResearchHandoffState,
	action: ResearchHandoffAction
): ResearchHandoffState {
	const next = { ...state };
	if (action === 'browser.focus') next.browserFocused = true;
	if (action === 'browser.copy_url' && state.browserFocused) next.addressCopied = true;
	if (action === 'editor.new_document' && state.addressCopied) next.documentCreated = true;
	if (action === 'editor.paste_content' && state.documentCreated) next.addressPasted = true;
	if (action === 'editor.save_as' && state.addressPasted) next.documentSaved = true;
	if (action === 'filesystem.search' && state.documentSaved) next.fileFound = true;
	if (action === 'filesystem.reveal' && state.fileFound) next.fileRevealed = true;
	return next;
}

function researchHandoffMilestoneSatisfied(progress: number, state: ResearchHandoffState): boolean {
	if (progress === 0) return state.browserFocused;
	if (progress === 1) return state.addressCopied;
	if (progress === 2) return state.documentCreated;
	if (progress === 3) return state.addressPasted;
	if (progress === 4) return state.documentSaved;
	if (progress === 5) return state.fileFound;
	return state.fileRevealed;
}

function researchHandoffTransition(
	state: ResearchHandoffState,
	action: ResearchHandoffAction
): { state: ResearchHandoffState; reward: number } {
	const next = applyResearchHandoffAction(state, action);
	if (!researchHandoffMilestoneSatisfied(state.progress, next)) return { state: next, reward: -2 };
	next.progress += 1;
	return { state: next, reward: next.progress === 7 ? 20 : 3 };
}

function trainResearchHandoffPolicy(episodes = 2800): {
	actions: ResearchHandoffAction[];
	statesVisited: number;
} {
	const qTable = new Map<string, number[]>();
	const random = seededRandom();
	const initialState = (): ResearchHandoffState => ({
		progress: 0,
		browserFocused: false,
		addressCopied: false,
		documentCreated: false,
		addressPasted: false,
		documentSaved: false,
		fileFound: false,
		fileRevealed: false
	});
	const valuesFor = (state: ResearchHandoffState) => {
		const key = [
			state.progress,
			Number(state.browserFocused),
			Number(state.addressCopied),
			Number(state.documentCreated),
			Number(state.addressPasted),
			Number(state.documentSaved),
			Number(state.fileFound),
			Number(state.fileRevealed)
		].join(':');
		let values = qTable.get(key);
		if (!values) {
			values = researchHandoffActionSpace.map(() => 0);
			qTable.set(key, values);
		}
		return values;
	};
	for (let episode = 0; episode < episodes; episode += 1) {
		let state = initialState();
		const epsilon = Math.max(0.05, 0.9 * (1 - episode / episodes));
		for (let step = 0; step < 48 && state.progress !== 7; step += 1) {
			const values = valuesFor(state);
			const actionIndex =
				random() < epsilon
					? Math.floor(random() * researchHandoffActionSpace.length)
					: bestAction(values);
			const outcome = researchHandoffTransition(state, researchHandoffActionSpace[actionIndex]);
			const future = outcome.state.progress === 7 ? 0 : Math.max(...valuesFor(outcome.state));
			values[actionIndex] += 0.25 * (outcome.reward - 0.05 + 0.9 * future - values[actionIndex]);
			state = outcome.state;
		}
	}
	const actions: ResearchHandoffAction[] = [];
	let state = initialState();
	while (state.progress !== 7) {
		const action = researchHandoffActionSpace[bestAction(valuesFor(state))];
		const outcome = researchHandoffTransition(state, action);
		if (outcome.state.progress === state.progress)
			throw new Error('Learned policy did not converge');
		actions.push(action);
		state = outcome.state;
	}
	return { actions, statesVisited: qTable.size };
}

export async function runResearchHandoffTask(
	runtime: TaskRuntime,
	command: string
): Promise<LearnedTaskResult | null> {
	const goal = compileResearchHandoffIntent(command);
	if (!goal) return null;
	const policy = trainResearchHandoffPolicy();
	const executions: LearnedTaskResult['executions'] = [];
	for (const action of policy.actions) {
		const input =
			action === 'editor.paste_content'
				? runtime.snapshot().clipboard[0]
				: action === 'editor.save_as'
					? { name: goal.filename, parent: 'Documents' }
					: action === 'filesystem.search'
						? goal.filename
						: undefined;
		const event = await runtime.dispatch({ node: action, input }, 'system');
		executions.push({
			action,
			status: event.result === 'ok' ? 'succeeded' : 'failed',
			message: event.detail
		});
		if (event.result === 'error')
			return buildResearchHandoffResult(command, goal, policy, executions, 'failed', event.detail);
	}
	return buildResearchHandoffResult(command, goal, policy, executions, 'succeeded', null);
}

export function compileWorkspaceSetupIntent(command: string): WorkspaceSetupIntent | null {
	const normalized = command.trim().replace(/\s+/g, ' ');
	if (
		!/\b(?:create|make|add)\b/i.test(normalized) ||
		!/\bworkspace\b/i.test(normalized) ||
		!/\bbrowser\b/i.test(normalized) ||
		!/\beditor\b/i.test(normalized) ||
		!/\b(?:beside|alongside|next to)\b/i.test(normalized) ||
		!/\b(?:note|document|file)\b/i.test(normalized) ||
		!/\bpaste\b/i.test(normalized) ||
		!/\bsave\b/i.test(normalized)
	)
		return null;
	const workspaceToken = normalized.match(
		/\b(?:create|make|add)(?:\s+a)?\s+(?:(second|third|fourth|[2-4](?:st|nd|rd|th)?)\s+)?workspace\b/i
	)?.[1];
	const workspaceNames: Record<string, number> = { second: 2, third: 3, fourth: 4 };
	const workspace = workspaceToken
		? (workspaceNames[workspaceToken.toLowerCase()] ?? Number.parseInt(workspaceToken, 10))
		: 2;
	const filename = normalized.match(
		/\bsave(?:\s+it)?\s+(?:as|with\s+(?:the\s+)?name)\s+["']?([\w.-]+)["']?/i
	)?.[1];
	const cleanFilename = filename?.trim().replace(/[.!?]+$/, '');
	return cleanFilename && workspace >= 2 && workspace <= 4
		? { type: 'workspace_setup', workspace, filename: cleanFilename }
		: null;
}

function applyWorkspaceSetupAction(
	state: WorkspaceSetupState,
	action: WorkspaceSetupAction
): WorkspaceSetupState {
	const next = { ...state };
	if (action === 'workspace.create') next.workspaceCreated = true;
	if (action === 'workspace.switch' && state.workspaceCreated) next.workspaceSelected = true;
	if (action === 'browser.open' && state.workspaceSelected) next.browserOpened = true;
	if (action === 'editor.open' && state.browserOpened) next.editorOpened = true;
	if (action === 'window.snap' && state.browserOpened && state.editorOpened)
		next.windowsArranged = true;
	if (action === 'editor.new_document' && state.windowsArranged) next.documentCreated = true;
	if (action === 'editor.paste_content' && state.documentCreated) next.contentPasted = true;
	if (action === 'editor.save_as' && state.contentPasted) next.documentSaved = true;
	return next;
}

function workspaceSetupMilestoneSatisfied(progress: number, state: WorkspaceSetupState): boolean {
	if (progress === 0) return state.workspaceCreated;
	if (progress === 1) return state.workspaceSelected;
	if (progress === 2) return state.browserOpened;
	if (progress === 3) return state.editorOpened;
	if (progress === 4) return state.windowsArranged;
	if (progress === 5) return state.documentCreated;
	if (progress === 6) return state.contentPasted;
	return state.documentSaved;
}

function workspaceSetupTransition(
	state: WorkspaceSetupState,
	action: WorkspaceSetupAction
): { state: WorkspaceSetupState; reward: number } {
	const next = applyWorkspaceSetupAction(state, action);
	if (!workspaceSetupMilestoneSatisfied(state.progress, next)) return { state: next, reward: -2 };
	next.progress += 1;
	return { state: next, reward: next.progress === 8 ? 20 : 3 };
}

function trainWorkspaceSetupPolicy(episodes = 3600): {
	actions: WorkspaceSetupAction[];
	statesVisited: number;
} {
	const qTable = new Map<string, number[]>();
	const random = seededRandom();
	const initialState = (): WorkspaceSetupState => ({
		progress: 0,
		workspaceCreated: false,
		workspaceSelected: false,
		browserOpened: false,
		editorOpened: false,
		windowsArranged: false,
		documentCreated: false,
		contentPasted: false,
		documentSaved: false
	});
	const valuesFor = (state: WorkspaceSetupState) => {
		const key = [
			state.progress,
			Number(state.workspaceCreated),
			Number(state.workspaceSelected),
			Number(state.browserOpened),
			Number(state.editorOpened),
			Number(state.windowsArranged),
			Number(state.documentCreated),
			Number(state.contentPasted),
			Number(state.documentSaved)
		].join(':');
		let values = qTable.get(key);
		if (!values) {
			values = workspaceSetupActionSpace.map(() => 0);
			qTable.set(key, values);
		}
		return values;
	};
	for (let episode = 0; episode < episodes; episode += 1) {
		let state = initialState();
		const epsilon = Math.max(0.05, 0.9 * (1 - episode / episodes));
		for (let step = 0; step < 56 && state.progress !== 8; step += 1) {
			const values = valuesFor(state);
			const actionIndex =
				random() < epsilon
					? Math.floor(random() * workspaceSetupActionSpace.length)
					: bestAction(values);
			const outcome = workspaceSetupTransition(state, workspaceSetupActionSpace[actionIndex]);
			const future = outcome.state.progress === 8 ? 0 : Math.max(...valuesFor(outcome.state));
			values[actionIndex] += 0.25 * (outcome.reward - 0.05 + 0.9 * future - values[actionIndex]);
			state = outcome.state;
		}
	}
	const actions: WorkspaceSetupAction[] = [];
	let state = initialState();
	while (state.progress !== 8) {
		const action = workspaceSetupActionSpace[bestAction(valuesFor(state))];
		const outcome = workspaceSetupTransition(state, action);
		if (outcome.state.progress === state.progress)
			throw new Error('Learned workspace policy did not converge');
		actions.push(action);
		state = outcome.state;
	}
	return { actions, statesVisited: qTable.size };
}

export async function runWorkspaceSetupTask(
	runtime: TaskRuntime,
	command: string
): Promise<LearnedTaskResult | null> {
	const goal = compileWorkspaceSetupIntent(command);
	if (!goal) return null;
	const clipboardContent = runtime.snapshot().clipboard[0];
	if (clipboardContent === undefined) throw new Error('The clipboard is empty');
	const policy = trainWorkspaceSetupPolicy();
	const executions: LearnedTaskResult['executions'] = [];
	for (const action of policy.actions) {
		const input =
			action === 'workspace.create' || action === 'workspace.switch'
				? goal.workspace
				: action === 'window.snap'
					? { window: 'editor', side: 'right', beside: 'browser' }
					: action === 'editor.paste_content'
						? clipboardContent
						: action === 'editor.save_as'
							? { name: goal.filename, parent: 'Documents' }
							: undefined;
		const event = await runtime.dispatch({ node: action, input }, 'system');
		executions.push({
			action,
			status: event.result === 'ok' ? 'succeeded' : 'failed',
			message: event.detail
		});
		if (event.result === 'error')
			return buildWorkspaceSetupResult(command, goal, policy, executions, 'failed', event.detail);
	}
	const finalState = runtime.snapshot();
	const arranged =
		finalState.workspace === goal.workspace &&
		finalState.windows.browser.open &&
		finalState.windows.browser.workspace === goal.workspace &&
		finalState.windows.browser.snap === 'left' &&
		finalState.windows.editor.open &&
		finalState.windows.editor.workspace === goal.workspace &&
		finalState.windows.editor.snap === 'right' &&
		finalState.editorText === clipboardContent;
	return buildWorkspaceSetupResult(
		command,
		goal,
		policy,
		executions,
		arranged ? 'succeeded' : 'failed',
		arranged ? null : 'The final workspace arrangement does not satisfy the compiled goal'
	);
}

export function compileDownloadArchiveIntent(command: string): DownloadArchiveIntent | null {
	const normalized = command.trim().replace(/\s+/g, ' ');
	if (
		!/\bbrowser\b/i.test(normalized) ||
		!/\bdownload\b/i.test(normalized) ||
		!/\b(?:current page|page)\b/i.test(normalized) ||
		!/\bfind\b/i.test(normalized) ||
		!/\brename\b/i.test(normalized) ||
		!/\bcreate\b/i.test(normalized) ||
		!/\bfolder\b/i.test(normalized) ||
		!/\bmove\b/i.test(normalized) ||
		!/\bcompress\b/i.test(normalized) ||
		!/\bopen\b/i.test(normalized)
	)
		return null;
	const filename = normalized.match(
		/\brename\s+(?:it|the\s+(?:download|file))\s+(?:(?:to|as)\s+)?["']?([\w.-]+)["']?/i
	)?.[1];
	const folder = normalized.match(/\bcreate\s+(?:an?\s+)?["']?([\w .-]+?)["']?\s+folder\b/i)?.[1];
	return filename && folder
		? {
				type: 'download_and_archive',
				filename: filename.trim().replace(/[.!?]+$/, ''),
				folder: folder.trim()
			}
		: null;
}

function applyDownloadArchiveAction(
	state: DownloadArchiveState,
	action: DownloadArchiveAction
): DownloadArchiveState {
	const next = { ...state };
	if (action === 'browser.open') next.browserOpened = true;
	if (action === 'browser.download' && state.browserOpened) next.pageDownloaded = true;
	if (action === 'filesystem.open_downloads' && state.pageDownloaded) next.downloadsOpened = true;
	if (action === 'filesystem.search' && state.downloadsOpened) next.downloadFound = true;
	if (action === 'filesystem.rename' && state.downloadFound) next.downloadRenamed = true;
	if (action === 'filesystem.create_folder' && state.downloadRenamed) next.folderCreated = true;
	if (action === 'filesystem.move' && state.folderCreated) next.downloadMoved = true;
	if (action === 'filesystem.compress' && state.downloadMoved) next.archiveCreated = true;
	if (action === 'filesystem.open' && state.archiveCreated) next.archiveLocationOpened = true;
	return next;
}

function downloadArchiveMilestoneSatisfied(progress: number, state: DownloadArchiveState): boolean {
	if (progress === 0) return state.browserOpened;
	if (progress === 1) return state.pageDownloaded;
	if (progress === 2) return state.downloadsOpened;
	if (progress === 3) return state.downloadFound;
	if (progress === 4) return state.downloadRenamed;
	if (progress === 5) return state.folderCreated;
	if (progress === 6) return state.downloadMoved;
	if (progress === 7) return state.archiveCreated;
	return state.archiveLocationOpened;
}

function downloadArchiveTransition(
	state: DownloadArchiveState,
	action: DownloadArchiveAction
): { state: DownloadArchiveState; reward: number } {
	const next = applyDownloadArchiveAction(state, action);
	if (!downloadArchiveMilestoneSatisfied(state.progress, next)) return { state: next, reward: -2 };
	next.progress += 1;
	return { state: next, reward: next.progress === 9 ? 20 : 3 };
}

function trainDownloadArchivePolicy(episodes = 4600): {
	actions: DownloadArchiveAction[];
	statesVisited: number;
} {
	const qTable = new Map<string, number[]>();
	const random = seededRandom();
	const initialState = (): DownloadArchiveState => ({
		progress: 0,
		browserOpened: false,
		pageDownloaded: false,
		downloadsOpened: false,
		downloadFound: false,
		downloadRenamed: false,
		folderCreated: false,
		downloadMoved: false,
		archiveCreated: false,
		archiveLocationOpened: false
	});
	const valuesFor = (state: DownloadArchiveState) => {
		const key = [
			state.progress,
			Number(state.browserOpened),
			Number(state.pageDownloaded),
			Number(state.downloadsOpened),
			Number(state.downloadFound),
			Number(state.downloadRenamed),
			Number(state.folderCreated),
			Number(state.downloadMoved),
			Number(state.archiveCreated),
			Number(state.archiveLocationOpened)
		].join(':');
		let values = qTable.get(key);
		if (!values) {
			values = downloadArchiveActionSpace.map(() => 0);
			qTable.set(key, values);
		}
		return values;
	};
	for (let episode = 0; episode < episodes; episode += 1) {
		let state = initialState();
		const epsilon = Math.max(0.05, 0.9 * (1 - episode / episodes));
		for (let step = 0; step < 72 && state.progress !== 9; step += 1) {
			const values = valuesFor(state);
			const actionIndex =
				random() < epsilon
					? Math.floor(random() * downloadArchiveActionSpace.length)
					: bestAction(values);
			const outcome = downloadArchiveTransition(state, downloadArchiveActionSpace[actionIndex]);
			const future = outcome.state.progress === 9 ? 0 : Math.max(...valuesFor(outcome.state));
			values[actionIndex] += 0.25 * (outcome.reward - 0.05 + 0.9 * future - values[actionIndex]);
			state = outcome.state;
		}
	}
	const actions: DownloadArchiveAction[] = [];
	let state = initialState();
	while (state.progress !== 9) {
		const action = downloadArchiveActionSpace[bestAction(valuesFor(state))];
		const outcome = downloadArchiveTransition(state, action);
		if (outcome.state.progress === state.progress)
			throw new Error('Learned download-and-archive policy did not converge');
		actions.push(action);
		state = outcome.state;
	}
	return { actions, statesVisited: qTable.size };
}

export async function runDownloadArchiveTask(
	runtime: TaskRuntime,
	command: string
): Promise<LearnedTaskResult | null> {
	const goal = compileDownloadArchiveIntent(command);
	if (!goal) return null;
	const policy = trainDownloadArchivePolicy();
	const executions: LearnedTaskResult['executions'] = [];
	const destination = `Downloads/${goal.folder}`;
	for (const action of policy.actions) {
		const input =
			action === 'browser.download'
				? { resource: 'current_page' }
				: action === 'filesystem.search'
					? { reference: 'previous_result' }
					: action === 'filesystem.rename'
						? { reference: 'current_item', name: goal.filename }
						: action === 'filesystem.create_folder'
							? { parent: 'Downloads', name: goal.folder }
							: action === 'filesystem.move'
								? { reference: 'current_item', parent: destination }
								: action === 'filesystem.compress'
									? { reference: 'current_item', archive_name: goal.filename }
									: action === 'filesystem.open'
										? destination
										: undefined;
		const event = await runtime.dispatch({ node: action, input }, 'system');
		executions.push({
			action,
			status: event.result === 'ok' ? 'succeeded' : 'failed',
			message: event.detail
		});
		if (event.result === 'error')
			return buildDownloadArchiveResult(command, goal, policy, executions, 'failed', event.detail);
	}
	const openedArchiveLocation = runtime.snapshot().filesPath === destination;
	return buildDownloadArchiveResult(
		command,
		goal,
		policy,
		executions,
		openedArchiveLocation ? 'succeeded' : 'failed',
		openedArchiveLocation ? null : 'The archive location was not open after execution'
	);
}

export function compileClipboardReportIntent(command: string): ClipboardReportIntent | null {
	const normalized = command.trim().replace(/\s+/g, ' ');
	if (
		!/\b(?:read|take|capture)\b/i.test(normalized) ||
		!/\bclipboard\b/i.test(normalized) ||
		!/\bcreate\b/i.test(normalized) ||
		!/\bfolder\b/i.test(normalized) ||
		!/\b(?:new document|new (?:text )?file)\b/i.test(normalized) ||
		!/\bpaste\b/i.test(normalized) ||
		!/\bsave\b/i.test(normalized) ||
		!/\bclose\b/i.test(normalized) ||
		!/\bfiles\b/i.test(normalized) ||
		!/\bfind\b/i.test(normalized) ||
		!/\bmove\b/i.test(normalized) ||
		!/\bstar\b/i.test(normalized)
	)
		return null;
	const folder = normalized.match(
		/\bcreate\s+(?:an?\s+)?(?:folder\s+)?["']?([\w .-]+?)["']?\s+folder\b/i
	)?.[1];
	const filename = normalized.match(
		/\bsave(?:\s+it)?\s+(?:as|with\s+(?:the\s+)?name)\s+["']?([\w.-]+)["']?/i
	)?.[1];
	return folder && filename
		? {
				type: 'clipboard_report',
				parent: 'Documents',
				folder: folder.trim(),
				filename: filename.trim().replace(/[.!?]+$/, '')
			}
		: null;
}

function applyClipboardReportAction(
	state: ClipboardReportState,
	action: ClipboardReportAction
): ClipboardReportState {
	const next = { ...state };
	if (action === 'clipboard.read') next.clipboardCaptured = true;
	if (action === 'filesystem.create_folder' && state.clipboardCaptured) next.folderCreated = true;
	if (action === 'editor.new_document' && state.folderCreated) next.documentCreated = true;
	if (action === 'editor.paste_content' && state.documentCreated) next.contentPasted = true;
	if (action === 'editor.save_as' && state.contentPasted) next.documentSaved = true;
	if (action === 'editor.close_document' && state.documentSaved) next.documentClosed = true;
	if (action === 'filesystem.open' && state.documentClosed) next.filesOpened = true;
	if (action === 'filesystem.search' && state.filesOpened) next.fileFound = true;
	if (action === 'filesystem.move' && state.fileFound) next.fileMoved = true;
	if (action === 'filesystem.star' && state.fileMoved) next.fileStarred = true;
	return next;
}

function clipboardReportMilestoneSatisfied(progress: number, state: ClipboardReportState): boolean {
	return [
		state.clipboardCaptured,
		state.folderCreated,
		state.documentCreated,
		state.contentPasted,
		state.documentSaved,
		state.documentClosed,
		state.filesOpened,
		state.fileFound,
		state.fileMoved,
		state.fileStarred
	][progress];
}

function clipboardReportTransition(
	state: ClipboardReportState,
	action: ClipboardReportAction
): { state: ClipboardReportState; reward: number } {
	const next = applyClipboardReportAction(state, action);
	if (!clipboardReportMilestoneSatisfied(state.progress, next)) return { state: next, reward: -2 };
	next.progress += 1;
	return { state: next, reward: next.progress === 10 ? 20 : 3 };
}

function trainClipboardReportPolicy(episodes = 5600): {
	actions: ClipboardReportAction[];
	statesVisited: number;
} {
	const qTable = new Map<string, number[]>();
	const random = seededRandom();
	const initialState = (): ClipboardReportState => ({
		progress: 0,
		clipboardCaptured: false,
		folderCreated: false,
		documentCreated: false,
		contentPasted: false,
		documentSaved: false,
		documentClosed: false,
		filesOpened: false,
		fileFound: false,
		fileMoved: false,
		fileStarred: false
	});
	const valuesFor = (state: ClipboardReportState) => {
		const key = [
			state.progress,
			state.clipboardCaptured,
			state.folderCreated,
			state.documentCreated,
			state.contentPasted,
			state.documentSaved,
			state.documentClosed,
			state.filesOpened,
			state.fileFound,
			state.fileMoved,
			state.fileStarred
		]
			.map(Number)
			.join(':');
		let values = qTable.get(key);
		if (!values) {
			values = clipboardReportActionSpace.map(() => 0);
			qTable.set(key, values);
		}
		return values;
	};
	for (let episode = 0; episode < episodes; episode += 1) {
		let state = initialState();
		const epsilon = Math.max(0.05, 0.9 * (1 - episode / episodes));
		for (let step = 0; step < 88 && state.progress !== 10; step += 1) {
			const values = valuesFor(state);
			const actionIndex =
				random() < epsilon
					? Math.floor(random() * clipboardReportActionSpace.length)
					: bestAction(values);
			const outcome = clipboardReportTransition(state, clipboardReportActionSpace[actionIndex]);
			const future = outcome.state.progress === 10 ? 0 : Math.max(...valuesFor(outcome.state));
			values[actionIndex] += 0.25 * (outcome.reward - 0.05 + 0.9 * future - values[actionIndex]);
			state = outcome.state;
		}
	}
	const actions: ClipboardReportAction[] = [];
	let state = initialState();
	while (state.progress !== 10) {
		const action = clipboardReportActionSpace[bestAction(valuesFor(state))];
		const outcome = clipboardReportTransition(state, action);
		if (outcome.state.progress === state.progress)
			throw new Error('Learned clipboard-report policy did not converge');
		actions.push(action);
		state = outcome.state;
	}
	return { actions, statesVisited: qTable.size };
}

export async function runClipboardReportTask(
	runtime: TaskRuntime,
	command: string
): Promise<LearnedTaskResult | null> {
	const goal = compileClipboardReportIntent(command);
	if (!goal) return null;
	const clipboardContent = runtime.snapshot().clipboard[0];
	if (clipboardContent === undefined) throw new Error('The clipboard is empty');
	const policy = trainClipboardReportPolicy();
	const executions: LearnedTaskResult['executions'] = [];
	const destination = `${goal.parent}/${goal.folder}`;
	for (const action of policy.actions) {
		const input =
			action === 'clipboard.read' || action === 'editor.paste_content'
				? clipboardContent
				: action === 'filesystem.create_folder'
					? { parent: goal.parent, name: goal.folder }
					: action === 'editor.save_as'
						? { name: goal.filename, parent: goal.parent }
						: action === 'filesystem.open'
							? goal.parent
							: action === 'filesystem.search'
								? goal.filename
								: action === 'filesystem.move'
									? { reference: 'current_item', parent: destination }
									: action === 'filesystem.star'
										? { reference: 'current_item', enabled: true }
										: undefined;
		const event = await runtime.dispatch({ node: action, input }, 'system');
		executions.push({
			action,
			status: event.result === 'ok' ? 'succeeded' : 'failed',
			message: event.detail
		});
		if (event.result === 'error')
			return buildClipboardReportResult(command, goal, policy, executions, 'failed', event.detail);
	}
	return buildClipboardReportResult(command, goal, policy, executions, 'succeeded', null);
}

function buildClipboardReportResult(
	command: string,
	goal: ClipboardReportIntent,
	policy: { actions: ClipboardReportAction[]; statesVisited: number },
	executions: LearnedTaskResult['executions'],
	status: LearnedTaskResult['status'],
	error: string | null
): LearnedTaskResult {
	return {
		command,
		goal,
		route: 'q_learning',
		training: {
			episodes: 5600,
			states: policy.statesVisited,
			actions: clipboardReportActionSpace.length
		},
		plan: policy.actions.map((action) => ({ action })),
		executions,
		status,
		error
	};
}

function buildDownloadArchiveResult(
	command: string,
	goal: DownloadArchiveIntent,
	policy: { actions: DownloadArchiveAction[]; statesVisited: number },
	executions: LearnedTaskResult['executions'],
	status: LearnedTaskResult['status'],
	error: string | null
): LearnedTaskResult {
	return {
		command,
		goal,
		route: 'q_learning',
		training: {
			episodes: 4600,
			states: policy.statesVisited,
			actions: downloadArchiveActionSpace.length
		},
		plan: policy.actions.map((action) => ({ action })),
		executions,
		status,
		error
	};
}

function buildWorkspaceSetupResult(
	command: string,
	goal: WorkspaceSetupIntent,
	policy: { actions: WorkspaceSetupAction[]; statesVisited: number },
	executions: LearnedTaskResult['executions'],
	status: LearnedTaskResult['status'],
	error: string | null
): LearnedTaskResult {
	return {
		command,
		goal,
		route: 'q_learning',
		training: {
			episodes: 3600,
			states: policy.statesVisited,
			actions: workspaceSetupActionSpace.length
		},
		plan: policy.actions.map((action) => ({ action })),
		executions,
		status,
		error
	};
}

function buildResearchHandoffResult(
	command: string,
	goal: ResearchHandoffIntent,
	policy: { actions: ResearchHandoffAction[]; statesVisited: number },
	executions: LearnedTaskResult['executions'],
	status: LearnedTaskResult['status'],
	error: string | null
): LearnedTaskResult {
	return {
		command,
		goal,
		route: 'q_learning',
		training: {
			episodes: 2800,
			states: policy.statesVisited,
			actions: researchHandoffActionSpace.length
		},
		plan: policy.actions.map((action) => ({ action })),
		executions,
		status,
		error
	};
}

function buildOrganizeNoteResult(
	command: string,
	goal: OrganizeNoteIntent,
	policy: { actions: OrganizeNoteAction[]; statesVisited: number },
	executions: LearnedTaskResult['executions'],
	status: LearnedTaskResult['status'],
	error: string | null
): LearnedTaskResult {
	return {
		command,
		goal,
		route: 'q_learning',
		training: {
			episodes: 2200,
			states: policy.statesVisited,
			actions: organizeNoteActionSpace.length
		},
		plan: policy.actions.map((action) => ({ action })),
		executions,
		status,
		error
	};
}

function buildFindAppendResult(
	command: string,
	goal: FindAppendIntent,
	policy: { actions: FindAppendAction[]; statesVisited: number },
	executions: LearnedTaskResult['executions'],
	status: LearnedTaskResult['status'],
	error: string | null
): LearnedTaskResult {
	return {
		command,
		goal,
		route: 'q_learning',
		training: {
			episodes: 1600,
			states: policy.statesVisited,
			actions: findAppendActionSpace.length
		},
		plan: policy.actions.map((action) => ({ action })),
		executions,
		status,
		error
	};
}

function buildResult(
	command: string,
	task: CompiledTask,
	policy: TrainedPolicy,
	executions: LearnedTaskResult['executions'],
	status: LearnedTaskResult['status'],
	error: string | null
): LearnedTaskResult {
	return {
		command,
		goal: task.goal,
		route: 'q_learning',
		training: {
			episodes: 1200,
			states: policy.statesVisited,
			actions: taskActionSpace.length
		},
		plan: policy.actions.map((action) => ({ action })),
		executions,
		status,
		error
	};
}
