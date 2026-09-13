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
type TaskMilestone =
	| 'clipboard_captured'
	| 'empty_document_created'
	| 'clipboard_content_pasted'
	| 'document_saved_with_name';

export interface ClipboardFileIntent {
	type: 'clipboard_to_text_file';
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
	goal: ClipboardFileIntent;
	route: 'q_learning';
	training: { episodes: number; states: number; actions: number };
	plan: Array<{ action: TaskAction }>;
	executions: Array<{
		action: TaskAction;
		status: 'succeeded' | 'failed';
		message: string;
	}>;
	status: 'succeeded' | 'failed';
	error: string | null;
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
