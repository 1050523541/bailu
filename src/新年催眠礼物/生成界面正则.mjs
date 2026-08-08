import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const dist_root = join(root, '../../dist/新年催眠礼物/界面');
const output_dir = join(root, '正则');

const jobs = [
  { entry: '首页', name: '开局首页' },
  { entry: '状态栏', name: '状态栏' },
];

mkdirSync(output_dir, { recursive: true });

for (const { entry, name } of jobs) {
  const html = readFileSync(join(dist_root, entry, 'index.html'), 'utf-8');
  const content = `\`\`\`\n${html}\n\`\`\`\n`;
  const output_path = join(output_dir, `${name}.txt`);
  writeFileSync(output_path, content, 'utf-8');
  console.log(`[生成界面正则] ${name}.txt (${content.length} chars)`);
}
