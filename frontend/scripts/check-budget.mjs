import { readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = '.svelte-kit/output/client';
const limits = { '.js': 200 * 1024, '.css': 80 * 1024 };
const failures = [];

function visit(directory) {
	for (const name of readdirSync(directory)) {
		const path = join(directory, name);
		const stats = statSync(path);
		if (stats.isDirectory()) visit(path);
		for (const [extension, limit] of Object.entries(limits)) {
			if (name.endsWith(extension) && stats.size > limit)
				failures.push(`${relative(root, path)} is ${stats.size} bytes (budget ${limit})`);
		}
	}
}

visit(root);
if (failures.length) {
	throw new Error(`Performance budget exceeded:\n${failures.join('\n')}`);
}
console.log('Performance budget passed: JS ≤ 200 KiB/file, CSS ≤ 80 KiB/file.');
