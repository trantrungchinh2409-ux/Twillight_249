param([string]$Python = '')
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
Set-Location $Root
if ($env:OS -ne 'Windows_NT') { throw 'Windows x64 required; no Linux cross-build.' }

function Run-Python([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed (exit $LASTEXITCODE)." }
}

if (-not $Python) {
    # Automatic local bootstrap; GitHub Actions supplies a pinned interpreter.
    $Tools = Join-Path $Root '.tools'
    $Target = Join-Path $Tools 'python3810'
    $Python = Join-Path $Target 'python.exe'
    if (-not (Test-Path $Python)) {
        New-Item -ItemType Directory -Force -Path $Tools | Out-Null
        [Net.ServicePointManager]::SecurityProtocol = 3072 # TLS 1.2; never disable certificate checks.
        $Installer = Join-Path $Tools 'python-3.8.10-amd64.exe'
        $Client = New-Object Net.WebClient
        try {
            $Client.DownloadFile('https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe', $Installer)
        } finally { $Client.Dispose() }
        $Signature = Get-AuthenticodeSignature $Installer
        if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
            throw 'Python installer signature could not be verified. Installation stopped.'
        }
        $InstallArgs = '/quiet InstallAllUsers=0 Include_launcher=0 Include_test=0 Include_pip=1 PrependPath=0 TargetDir="' + $Target + '"'
        $Process = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -Wait -PassThru
        if ($Process.ExitCode -ne 0) { throw "Python installer failed: $($Process.ExitCode)" }
    }
}
Run-Python $Python @('-c', 'import sys,struct; assert sys.version_info[:3] == (3,8,10); assert struct.calcsize(chr(80)) == 8')
Run-Python $Python @('-m', 'venv', '.venv-build')
$BuildPython = Join-Path $Root '.venv-build\Scripts\python.exe'
Run-Python $BuildPython @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', 'requirements-build.txt')
Run-Python $BuildPython @('-m', 'unittest', 'discover', '-s', 'tests', '-v')
Run-Python $BuildPython @('run_bot.py', '--self-test')
Run-Python $BuildPython @('-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--console', '--name', 'JAT-Design-0.1.0-dev', 'run_bot.py')
$Exe = Join-Path $Root 'dist\JAT-Design-0.1.0-dev.exe'
if (-not (Test-Path $Exe)) { throw 'EXE was not created.' }
Run-Python $BuildPython @('scripts/verify_exe.py', $Exe)
Run-Python $BuildPython @('scripts/package_source.py')
Write-Output 'Built offline candidate. Windows 7 and real Zalo behavior are NOT verified.'
