# Resumable upload of data.zip to the GPU server. Run on the laptop (Windows PowerShell; uses the built-in OpenSSH).
# Picks up from however many bytes the server already has, and keeps retrying after a dropped connection
# until the server copy is the same size as the local one.
#
#   powershell -ExecutionPolicy Bypass -File upload_data.ps1 -Zip C:\path\to\data.zip
#
# Without an SSH key you'll be asked for the password on every attempt (set up a key to make it hands-free).
param(
    [Parameter(Mandatory = $true)][string]$Zip,
    [string]$Server = "dal058778@10.152.44.18",
    [string]$Remote = "/mnt/Data/Tushaar/nextrun/data.zip"
)
$ErrorActionPreference = "Stop"
$total = (Get-Item $Zip).Length

while ($true) {
    # if the server copy went missing (e.g. a cancelled VS Code upload deleted it), restore the hard-linked backup
    $have = ssh $Server "[ -f '$Remote' ] || ln '$Remote.keep' '$Remote' 2>/dev/null; stat -c %s '$Remote' 2>/dev/null || echo 0"
    if ($LASTEXITCODE -eq 0) {
        $have = [int64]($have | Select-Object -Last 1)
        Write-Host ("{0:T}  server has {1:N1} of {2:N1} GB" -f (Get-Date), ($have / 1e9), ($total / 1e9))
        if ($have -eq $total) { Write-Host "upload complete"; break }
        if ($have -gt $total) { throw "server file is bigger than the local one; wrong file?" }
        "reput `"$Zip`" `"$Remote`"" | sftp $Server
    }
    Write-Host "connection dropped or upload interrupted; retrying in 30 s (Ctrl+C to stop)"
    Start-Sleep -Seconds 30
}
