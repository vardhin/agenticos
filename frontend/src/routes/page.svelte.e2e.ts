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
