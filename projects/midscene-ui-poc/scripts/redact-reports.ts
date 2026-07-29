import { readdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDir = dirname(fileURLToPath(import.meta.url));
const reportDir = join(currentDir, '../reports');
const rules: Array<[RegExp, string]> = [
  [/1[3-9]\d{9}/g, '***手机号已脱敏***'],
  [/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '***邮箱已脱敏***'],
  [/(sk-|Bearer\s+)[A-Za-z0-9_\-.]+/g, '***密钥或Token已脱敏***'],
  [/cookie:\s*[^;\n]+/gi, 'cookie: ***已脱敏***']
];

async function walk(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = await Promise.all(entries.map(async (entry) => {
    const fullPath = join(dir, entry.name);
    return entry.isDirectory() ? walk(fullPath) : [fullPath];
  }));
  return files.flat();
}

const files = await walk(reportDir);
const targetFiles = files.filter((file) => /\.(html|json|log|txt)$/i.test(file));

for (const file of targetFiles) {
  let text = await readFile(file, 'utf8');
  for (const [pattern, replacement] of rules) {
    text = text.replace(pattern, replacement);
  }
  await writeFile(file, text, 'utf8');
}

console.log(`Redacted ${targetFiles.length} report files.`);
