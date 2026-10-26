# Read-only TLS validation using Windows/.NET. Honor execution policy; never bypass it.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
function Emit([string]$Name, [string]$Value) { [Console]::Out.WriteLine($Name + '=' + $Value) }
try {
    if ([Net.ServicePointManager]::ServerCertificateValidationCallback -ne $null) {
        Emit 'WINDOWS_HTTPS' 'NOT_RUN'
        Emit 'WINDOWS_ERROR' 'NONDEFAULT_CERT_VALIDATION_CALLBACK'
        exit 2
    }
    # TLS 1.2 for this diagnostic process only. No registry or machine policy changes.
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]3072
    Emit 'WINDOWS_PROTOCOL' 'TLS12_PROCESS_ONLY'
    $uri = New-Object System.Uri -ArgumentList 'https://bot-api.zaloplatforms.com/'
    $request = [Net.HttpWebRequest]::Create($uri)
    $request.Method = 'HEAD'
    $request.AllowAutoRedirect = $false
    $request.Timeout = 15000
    $request.ReadWriteTimeout = 15000
    $route = 'DIRECT'
    try {
        if ($request.Proxy -ne $null -and -not $request.Proxy.IsBypassed($uri)) {
            $p = $request.Proxy.GetProxy($uri)
            $route = $p.Scheme + '://' + $p.DnsSafeHost.ToLowerInvariant() + ':' + $p.Port
        }
    } catch { $route = 'UNKNOWN' }
    # Python captures this IPC field but never prints the endpoint or credentials.
    Emit 'ROUTE_B64' ([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($route)))
    $response = $null
    try {
        $response = $request.GetResponse()
        Emit 'WINDOWS_HTTPS' 'PASS'
        Emit 'WINDOWS_HTTP' ([string][int]$response.StatusCode)
    } catch [Net.WebException] {
        $e = $_.Exception
        if ($e.Status -eq [Net.WebExceptionStatus]::ProtocolError -and $e.Response -ne $null) {
            $response = $e.Response
            Emit 'WINDOWS_HTTPS' 'PASS'
            Emit 'WINDOWS_HTTP' ([string][int]$response.StatusCode)
        } else {
            Emit 'WINDOWS_HTTPS' 'FAIL'
            Emit 'WINDOWS_ERROR' ([string]$e.Status)
        }
    } finally { if ($response -ne $null) { $response.Close() } }
    $certificate = $request.ServicePoint.Certificate
    if ($certificate -eq $null) {
        Emit 'CHAIN_AVAILABLE' 'NO'
        exit 0
    }
    # Certificate metadata can exist even when validation failed. Never override validation.
    $leaf = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 -ArgumentList $certificate
    Emit 'LEAF_DER' ([Convert]::ToBase64String($leaf.RawData))
    $chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
    if ($chain.ChainPolicy.VerificationFlags -ne [System.Security.Cryptography.X509Certificates.X509VerificationFlags]::NoFlag) {
        Emit 'CHAIN_AVAILABLE' 'NO'
        exit 2
    }
    $chain.ChainPolicy.UrlRetrievalTimeout = [TimeSpan]::FromSeconds(5)
    $built = $chain.Build($leaf)
    Emit 'CHAIN_AVAILABLE' 'YES'
    Emit 'WINDOWS_CHAIN_VALID' $(if ($built) { 'YES' } else { 'NO' })
    # Status values and public DER only, not subject/issuer names or HTTP body.
    $flags = 0
    foreach ($status in $chain.ChainStatus) { $flags = $flags -bor [int]$status.Status }
    Emit 'CHAIN_STATUS_FLAGS' ([string]$flags)
    $index = 0
    foreach ($item in $chain.ChainElements) {
        if ($index -ge 16) { break }
        if ($item.Certificate.RawData.Length -le 65536) {
            Emit ('CERT_' + $index + '_DER') ([Convert]::ToBase64String($item.Certificate.RawData))
        }
        $index++
    }
    $chain.Reset()
} catch {
    Emit 'WINDOWS_PROBE_ERROR' 'UNAVAILABLE_POLICY_RUNTIME_OR_TLS12'
    exit 2
}
