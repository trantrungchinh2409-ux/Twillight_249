"""Explicit allowlist: never include credentials, databases, caches or .git."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package():
    output = ROOT / 'dist' / 'JAT-Design-Windows11-Polling-Test-source.zip'
    output.parent.mkdir(exist_ok=True)
    files = [ROOT / name for name in
             ('README.md', 'requirements.txt', 'requirements-build.txt',
              'run_bot.py', '.gitignore', 'index.html', 'START_TEST.bat',
              'SWITCH_TO_POLLING.bat', 'RESTORE_WEBHOOK.bat', 'SEND_ONCE.bat',
              'README_WINDOWS11.md', 'README_VI.md', 'DEPLOY_REPORT.md',
              'package.json', 'package-lock.json', 'tsconfig.json',
              'tsconfig.test.json', 'wrangler.jsonc', '.node-version',
              '.dev.vars.example')]
    for directory, pattern in (('jat_design', '*.py'), ('tests', '*.py'),
                               ('scripts', '*.py'), ('scripts', '*.ps1'),
                               ('docs', '*.md'), ('.github/workflows', '*.yml'),
                               ('src', '*.ts'), ('worker-tests', '*.ts'),
                               ('migrations', '*.sql'), ('tools', '*.py')):
        files.extend((ROOT / directory).glob(pattern))
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            if not path.is_file() or path.is_symlink():
                raise RuntimeError('Missing or unsafe package input: ' + path.name)
            archive.write(path, 'JAT-Design/' + path.relative_to(ROOT).as_posix())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest + '  ' + output.name + '\n', encoding='ascii')
    print(output.name, digest)
    return output


if __name__ == '__main__':
    package()
