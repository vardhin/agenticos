import { expect, test } from '@playwright/test';

test.use({ viewport: { width: 1440, height: 1024 }, deviceScaleFactor: 1 });

test('desktop shell renders and routes human and remote commands', async ({ page, request }) => {
	const consoleErrors: string[] = [];
	page.on('console', (message) => {
		if (message.type() === 'error') consoleErrors.push(message.text());
	});

	await page.goto('/');
	await page.evaluate(() => document.fonts.ready);
	await expect(page.getByRole('main', { name: 'AgentOS desktop' })).toBeVisible();
	await expect(page.getByRole('region', { name: 'Text Editor window' })).toBeVisible();
	await expect(page.getByRole('region', { name: 'Control Graph Inspector window' })).toBeVisible();
	await page.screenshot({ path: 'artifacts/implementation-1440x1024.png' });

	await page.getByRole('button', { name: 'Network' }).click();
	await expect(page.getByRole('region', { name: 'Wi-Fi controls' })).toBeVisible();
	await page.getByRole('button', { name: 'PineHouse Good' }).click();
	await expect(page.getByRole('button', { name: 'PineHouse Connected' })).toBeVisible();

	await page.getByRole('button', { name: 'Applications' }).click();
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
