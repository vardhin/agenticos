import { expect, test } from '@playwright/test';

test.use({ viewport: { width: 1440, height: 1024 }, deviceScaleFactor: 1 });

test.beforeEach(async ({ request }) => {
	await request.put('/backend-api/state', { data: { value: {} } });
});

test('launcher submits natural-language intents to the backend', async ({ page, request }) => {
	await request.post('/backend-api/agent/tasks', { data: { command: 'wifi off' } });
	await page.goto('/');

	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	const launcher = page.getByRole('region', { name: 'Application menu' });
	await launcher.getByRole('textbox', { name: 'Search applications' }).fill('on wifi');
	await launcher.getByRole('textbox', { name: 'Search applications' }).press('Enter');

	await expect(launcher.getByRole('status')).toContainText('Wi-Fi enabled');
	await expect(launcher.getByRole('status')).toContainText('deterministic · 1 action');
	const state = await request.get('/backend-api/wifi/state');
	expect((await state.json()).enabled).toBe(true);
});

test('learned policy completes a clipboard to saved text-file trajectory', async ({
	page,
	request
}) => {
	const name = `hero-${Date.now()}`;
	await page.goto('/');
	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	const launcher = page.getByRole('region', { name: 'Application menu' });
	await launcher
		.getByRole('textbox', { name: 'Search applications' })
		.fill(
			`first take the clipboard content, make a new text file, paste it there, then save it with name "${name}"`
		);
	await launcher.getByRole('textbox', { name: 'Search applications' }).press('Enter');

	const editor = page.getByRole('region', { name: 'Text Editor window' });
	await expect(editor).toBeVisible();
	await expect(editor).toContainText(`${name}.txt`);
	await expect(page.getByRole('textbox', { name: 'Document text' })).toHaveValue(
		'https://agentos.dev/docs'
	);

	await expect
		.poll(async () => {
			const response = await request.get('/backend-api/files/search', {
				params: { q: `${name}.txt` }
			});
			return (await response.json()).items[0]?.name;
		})
		.toBe(`${name}.txt`);
	const search = await request.get('/backend-api/files/search', { params: { q: `${name}.txt` } });
	const file = (await search.json()).items[0];
	const saved = await request.get(`/backend-api/files/${file.id}`, {
		params: { include_content: true }
	});
	expect((await saved.json()).content).toBe('https://agentos.dev/docs');
	await expect
		.poll(async () => {
			const response = await request.get('/backend-api/events');
			const policyNodes = (await response.json()).items
				.map((event: { node: string }) => event.node)
				.filter((node: string) =>
					[
						'clipboard.read',
						'window.editor.new',
						'window.editor.paste',
						'window.editor.save'
					].includes(node)
				);
			return policyNodes.slice(0, 4);
		})
		.toEqual(['window.editor.save', 'window.editor.paste', 'window.editor.new', 'clipboard.read']);
});

test('learned policy finds a file and appends the current clipboard item', async ({
	page,
	request
}) => {
	const basename = `hero-${Date.now()}`;
	const created = await request.post('/backend-api/files', {
		data: {
			parent_path: 'Documents',
			name: `${basename}.txt`,
			kind: 'text',
			content: 'Opening line: '
		}
	});
	expect(created.ok()).toBeTruthy();
	const file = await created.json();

	await page.goto('/');
	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	const launcher = page.getByRole('region', { name: 'Application menu' });
	await launcher
		.getByRole('textbox', { name: 'Search applications' })
		.fill(
			`Find the file named ${basename}, open it, add the current clipboard content at the end, and save it.`
		);
	await launcher.getByRole('textbox', { name: 'Search applications' }).press('Enter');

	await expect(page.getByRole('region', { name: 'Text Editor window' })).toContainText(
		`${basename}.txt`
	);
	await expect(page.getByRole('textbox', { name: 'Document text' })).toHaveValue(
		'Opening line: https://agentos.dev/docs'
	);
	await expect
		.poll(async () => {
			const response = await request.get(`/backend-api/files/${file.id}`, {
				params: { include_content: true }
			});
			return (await response.json()).content;
		})
		.toBe('Opening line: https://agentos.dev/docs');
	await expect
		.poll(async () => {
			const response = await request.get('/backend-api/events');
			const actionIds = [
				'filesystem.search',
				'filesystem.open_file',
				'clipboard.read',
				'editor.insert',
				'editor.save'
			];
			return (await response.json()).items
				.map((event: { node: string }) => event.node)
				.filter((node: string) => actionIds.includes(node))
				.slice(0, 5);
		})
		.toEqual([
			'editor.save',
			'editor.insert',
			'clipboard.read',
			'filesystem.open_file',
			'filesystem.search'
		]);
});

test('learned policy organizes a clipboard note into a new folder', async ({ page, request }) => {
	const suffix = Date.now();
	const folder = `Projects-${suffix}`;
	const basename = `brief-${suffix}`;
	await page.goto('/');
	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	const launcher = page.getByRole('region', { name: 'Application menu' });
	await launcher
		.getByRole('textbox', { name: 'Search applications' })
		.fill(
			`Create a ${folder} folder in Documents, make a note from the clipboard, save it as ${basename}, and move it into ${folder}.`
		);
	await launcher.getByRole('textbox', { name: 'Search applications' }).press('Enter');

	await expect(page.getByRole('region', { name: 'Text Editor window' })).toContainText(
		`${basename}.txt`
	);
	await expect
		.poll(async () => {
			const response = await request.get('/backend-api/files', {
				params: { path: `Documents/${folder}` }
			});
			return response.ok() ? (await response.json()).items : [];
		})
		.toContainEqual(expect.objectContaining({ name: `${basename}.txt` }));
	const search = await request.get('/backend-api/files/search', {
		params: { q: `${basename}.txt` }
	});
	const file = (await search.json()).items[0];
	const saved = await request.get(`/backend-api/files/${file.id}`, {
		params: { include_content: true }
	});
	expect((await saved.json()).content).toBe('https://agentos.dev/docs');
	await expect
		.poll(async () => {
			const response = await request.get('/backend-api/events');
			const actionIds = [
				'filesystem.open',
				'filesystem.create_folder',
				'clipboard.read',
				'editor.new_document',
				'editor.paste_content',
				'editor.save_as'
			];
			return (await response.json()).items
				.map((event: { node: string }) => event.node)
				.filter((node: string) => actionIds.includes(node))
				.slice(0, 6);
		})
		.toEqual([
			'editor.save_as',
			'editor.paste_content',
			'editor.new_document',
			'clipboard.read',
			'filesystem.create_folder',
			'filesystem.open'
		]);
});

test('learned policy hands the current browser address off to a revealed source note', async ({
	page,
	request
}) => {
	const basename = `source-${Date.now()}`;
	await page.goto('/');
	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	const launcher = page.getByRole('region', { name: 'Application menu' });
	await launcher
		.getByRole('textbox', { name: 'Search applications' })
		.fill(
			`Copy the browser address, create a source note, paste the address, save it as ${basename}, then reveal it in Files.`
		);
	await launcher.getByRole('textbox', { name: 'Search applications' }).press('Enter');

	const filesWindow = page.getByRole('region', { name: 'Files window' });
	await expect(filesWindow).toBeVisible();
	await expect(filesWindow.locator('.folder-grid button.selected')).toContainText(
		`${basename}.txt`
	);
	const search = await request.get('/backend-api/files/search', {
		params: { q: `${basename}.txt` }
	});
	const file = (await search.json()).items[0];
	const saved = await request.get(`/backend-api/files/${file.id}`, {
		params: { include_content: true }
	});
	expect((await saved.json()).content).toBe('https://example.com');
	await expect
		.poll(async () => {
			const response = await request.get('/backend-api/events');
			const actionIds = [
				'browser.focus',
				'browser.copy_url',
				'editor.new_document',
				'editor.paste_content',
				'editor.save_as',
				'filesystem.search',
				'filesystem.reveal'
			];
			return (await response.json()).items
				.map((event: { node: string }) => event.node)
				.filter((node: string) => actionIds.includes(node))
				.slice(0, 7);
		})
		.toEqual([
			'filesystem.reveal',
			'filesystem.search',
			'editor.save_as',
			'editor.paste_content',
			'editor.new_document',
			'browser.copy_url',
			'browser.focus'
		]);
});

test('desktop shell renders and routes human and remote commands', async ({ page, request }) => {
	const consoleErrors: string[] = [];
	page.on('console', (message) => {
		if (message.type() === 'error') consoleErrors.push(message.text());
	});

	await page.goto('/');
	await page.evaluate(() => document.fonts.ready);
	await expect(page.getByRole('main', { name: 'AgentOS desktop' })).toBeVisible();
	await page.evaluate(() =>
		window.dispatchEvent(new CustomEvent('agentos:command', { detail: { node: 'panel.editor' } }))
	);
	await page.evaluate(() =>
		window.dispatchEvent(
			new CustomEvent('agentos:command', { detail: { node: 'panel.inspector' } })
		)
	);
	await expect(page.getByRole('region', { name: 'Text Editor window' })).toBeVisible();
	await expect(page.getByRole('region', { name: 'Control Graph Inspector window' })).toBeVisible();
	await page.screenshot({ path: 'artifacts/implementation-1440x1024.png' });

	await page.getByRole('button', { name: 'Network', exact: true }).click();
	await expect(page.getByRole('region', { name: 'Wi-Fi controls' })).toBeVisible();
	await page.getByRole('button', { name: 'PineHouse Good' }).click();
	await expect(page.getByRole('button', { name: 'PineHouse Connected' })).toBeVisible();

	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	await expect(page.getByRole('region', { name: 'Application menu' })).toBeVisible();
	await page.getByRole('textbox', { name: 'Search applications' }).fill('Files');
	await page.getByRole('button', { name: 'Files Browse files and folders' }).click();
	await expect(page.getByRole('region', { name: 'Files window' })).toBeVisible();

	const response = await request.post('/api/control', { data: { node: 'panel.network' } });
	expect(response.ok()).toBeTruthy();
	await expect(
		page.getByTitle('Network panel opened').or(page.getByTitle('Network panel closed')).first()
	).toBeVisible();
	expect(consoleErrors).toEqual([]);
});

test('core desktop surfaces share state and remain keyboard accessible', async ({ page }) => {
	await page.goto('/');
	await page.evaluate(() => document.fonts.ready);

	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	await expect(page.getByRole('region', { name: 'Application menu' })).toBeVisible();
	await page.getByRole('textbox', { name: 'Search applications' }).fill('settings');
	await page.getByRole('button', { name: 'Settings Configure your system' }).click();
	await expect(page.getByRole('region', { name: 'Settings window' })).toBeVisible();

	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Applications' })
		.click();
	await page.getByRole('textbox', { name: 'Search applications' }).fill('software');
	await page.getByRole('button', { name: 'Software Install and update apps' }).click();
	await expect(page.getByRole('region', { name: 'Software window' })).toBeVisible();
	await page.getByRole('button', { name: 'Install', exact: true }).first().click();
	await expect(page.getByRole('button', { name: 'Remove', exact: true }).first()).toBeVisible();

	await page.getByRole('button', { name: 'Overview' }).click();
	await expect(page.getByLabel('Workspace overview')).toBeVisible();
	await page.getByRole('button', { name: /2.*windows/ }).click();
	await expect(page.getByLabel('Workspace overview')).toBeHidden();

	await page.getByRole('button', { name: /Volume/ }).click();
	await expect(page.getByRole('region', { name: 'Control Centre' })).toBeVisible();
	await page.getByRole('button', { name: /Do Not Disturb/ }).click();
	await expect(page.getByRole('button', { name: /Do Not Disturb.*On/ })).toBeVisible();

	await page.getByRole('button', { name: 'Clipboard history' }).click();
	await expect(page.getByRole('region', { name: 'Clipboard history' })).toBeVisible();
	await page.getByRole('button', { name: 'Screen capture' }).click();
	await expect(page.getByRole('region', { name: 'Screen capture' })).toBeVisible();
	await page.screenshot({ path: 'artifacts/expanded-desktop-1440x1024.png' });
});

test('text files can be created, edited, saved, reopened and edited again', async ({ page }) => {
	await page.goto('/');
	const name = `agent-note-${Date.now()}.txt`;

	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Files' })
		.click();
	await expect(page.getByRole('region', { name: 'Files window' })).toBeVisible();
	page.once('dialog', (dialog) => dialog.accept(name));
	await page.getByRole('button', { name: '+ File' }).click();

	const editor = page.getByRole('region', { name: 'Text Editor window' });
	await expect(editor).toBeVisible();
	await expect(editor).toContainText(name);
	const document = page.getByRole('textbox', { name: 'Document text' });
	await document.fill('First line\nSecond line');
	await page.getByRole('button', { name: 'Save document' }).click();
	await expect(editor).toContainText('Saved');

	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Files' })
		.click();
	await page.getByRole('textbox', { name: 'Search files' }).fill(name);
	const file = page
		.getByRole('region', { name: 'Files window' })
		.getByRole('button', { name: new RegExp(name) });
	await expect(file).toBeVisible();
	await file.dblclick();
	await expect(document).toHaveValue('First line\nSecond line');

	await document.fill('Updated and persisted');
	await document.press('Control+s');
	await expect(editor).toContainText('Saved');
});

test('terminal executes commands against the virtual filesystem', async ({ page }) => {
	await page.goto('/');
	await page
		.getByRole('navigation', { name: 'System panel' })
		.getByRole('button', { name: 'Terminal' })
		.click();
	const terminal = page.getByRole('region', { name: 'Terminal window' });
	await expect(terminal).toBeVisible();
	const input = page.getByRole('textbox', { name: 'Terminal command' });
	await input.fill('pwd');
	await input.press('Enter');
	await expect(terminal).toContainText('/home/agentos');
	await input.fill('help');
	await input.press('Enter');
	await expect(terminal).toContainText(
		'Commands: help, pwd, ls, cd, cat, touch, mkdir, echo, history, clear'
	);
});
