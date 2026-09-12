import { defineConfig } from '@playwright/test';

export default defineConfig({
	use: { baseURL: 'http://127.0.0.1:4173' },
	webServer: [
		{
			command: '../backend/.venv/bin/uvicorn backend.app:app --app-dir ../backend/src --port 8000',
			port: 8000,
			reuseExistingServer: true
		},
		{ command: 'npm run build && npm run preview', port: 4173, reuseExistingServer: true }
	],
	testMatch: '**/*.e2e.{ts,js}'
});
