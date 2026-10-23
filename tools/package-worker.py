"""Export Worker source only; explicit allowlist excludes local secrets/state."""
from pathlib import Path
import hashlib
import zipfile
root = Path(__file__).resolve().parents[1]
files = [root / name for name in ('package.json', 'package-lock.json', 'tsconfig.json',
         'tsconfig.test.json', 'wrangler.jsonc', '.dev.vars.example', '.gitignore',
         'README_VI.md', 'DEPLOY_REPORT.md', '.node-version')]
for folder, pattern in [('src', '*.ts'), ('worker-tests', '*.ts'), ('migrations', '*.sql'),
                        ('docs', '*.md'), ('tools', '*.py')]:
    files.extend((root / folder).glob(pattern))
files.append(root / '.github/workflows/worker.yml')
out = root / 'dist/JAT-Design-Cloudflare-V0.1-source.zip'
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(set(files)):
        if not path.is_file() or path.is_symlink():
            raise RuntimeError('Missing or unsafe input: ' + path.name)
        archive.write(path, 'JAT-Design/' + path.relative_to(root).as_posix())
digest = hashlib.sha256(out.read_bytes()).hexdigest()
out.with_suffix('.zip.sha256').write_text(digest + '  ' + out.name + '\n')
print(out.name, digest)
