import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

const clients = new Set<ReadableStreamDefaultController<Uint8Array>>();
const encoder = new TextEncoder();

export const GET: RequestHandler = () => {
	let keepAlive: ReturnType<typeof setInterval>;
	let clientController: ReadableStreamDefaultController<Uint8Array>;
	const stream = new ReadableStream<Uint8Array>({
		start(controller) {
			clientController = controller;
			clients.add(controller);
			controller.enqueue(encoder.encode(`event: ready\ndata: {"connected":true}\n\n`));
			keepAlive = setInterval(() => controller.enqueue(encoder.encode(': keep-alive\n\n')), 20_000);
		},
		cancel() {
			clients.delete(clientController);
			clearInterval(keepAlive);
		}
	});
	return new Response(stream, {
		headers: {
			'content-type': 'text/event-stream',
			'cache-control': 'no-cache',
			connection: 'keep-alive'
		}
	});
};

export const POST: RequestHandler = async ({ request }) => {
	const body = await request.json().catch(() => null);
	if (!body || typeof body.node !== 'string')
		return json(
			{ accepted: false, error: 'Expected { "node": string, "input"?: unknown }' },
			{ status: 400 }
		);
	const command = { node: body.node, input: body.input, source: 'remote' };
	const packet = encoder.encode(`event: command\ndata: ${JSON.stringify(command)}\n\n`);
	for (const client of clients) {
		try {
			client.enqueue(packet);
		} catch {
			clients.delete(client);
		}
	}
	return json({ accepted: true, command, listeners: clients.size });
};
