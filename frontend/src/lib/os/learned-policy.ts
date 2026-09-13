import type { OSCommand } from './types';

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
type LearnedAction = TaskAction | FindAppendAction | OrganizeNoteAction;
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
	goal: ClipboardFileIntent | FindAppendIntent | OrganizeNoteIntent;
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

export interface TaskRuntime {
	dispatch(
		command: OSCommand,
		source?: 'human' | 'remote' | 'system'
	): Promise<{ result: 'ok' | 'error'; detail: string }>;
	snapshot(): { clipboard: string[]; editorText: string };
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
