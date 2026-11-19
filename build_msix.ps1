<#
.SYNOPSIS
  Genera il pacchetto .msix per Microsoft Store con makeappx.exe (Windows SDK).
.PARAMETER Version
  Versione del pacchetto (4 numeri, es. 1.0.1.0). Se omessa resta quella del manifest.
.PARAMETER PfxPath
  (Opzionale) certificato .pfx per firmare il pacchetto in locale (sideload/test).
  Per l'upload su Partner Center NON serve: lo Store firma il pacchetto.
.PARAMETER PfxPassword
  Password del .pfx.
.PARAMETER IdentityName
  Package/Identity/Name di Partner Center (es. 12345Publisher.MarkItDownApp).
.PARAMETER Publisher
  Package/Identity/Publisher di Partner Center (es. CN=XXXXXXXX-XXXX-...).
.PARAMETER PublisherDisplayName
  Nome editore mostrato nello Store.
.PARAMETER SelfSignTest
  Crea un certificato autofirmato (Subject = Publisher del manifest) e firma il
  pacchetto SOLO per test locale. Non e' per lo Store. Non modifica i
  certificati attendibili del sistema: per installare il pacchetto firmato
  importa a mano dist\MarkItDownTest.cer in "Persone attendibili" (admin).
.PARAMETER SkipExe
  Non ricompilare l'exe se dist\MarkItDownApp esiste gia'.
#>
param(
    [string]$Version,
    [string]$PfxPath,
    [string]$PfxPassword,
    [string]$IdentityName,
    [string]$Publisher,
    [string]$PublisherDisplayName,
    [switch]$SelfSignTest,
    [switch]$SkipExe
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$appDir = "dist\MarkItDownApp"
if (-not $SkipExe -or -not (Test-Path "$appDir\MarkItDownApp.exe")) {
    & "$PSScriptRoot\build_exe.ps1"          # onedir
}
if (-not (Test-Path "$appDir\MarkItDownApp.exe")) { throw "Manca $appDir\MarkItDownApp.exe" }

# Trova makeappx / signtool nel Windows SDK
function Find-SdkTool([string]$name) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $root = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (Test-Path $root) {
        $f = Get-ChildItem $root -Recurse -Filter $name -ErrorAction SilentlyContinue |
             Where-Object { $_.FullName -match "\\x64\\" } |
             Sort-Object FullName -Descending | Select-Object -First 1
        if ($f) { return $f.FullName }
    }
    return $null
}
$makeappx = Find-SdkTool "makeappx.exe"
if (-not $makeappx) {
    throw "makeappx.exe non trovato. Installa il Windows 10/11 SDK: winget install Microsoft.WindowsSDK.10.0.26100"
}

# Layout del pacchetto
$layout = "build\msix_layout"
if (Test-Path $layout) { Remove-Item $layout -Recurse -Force }
New-Item -ItemType Directory -Force $layout | Out-Null
Copy-Item "$appDir\*" $layout -Recurse -Force
New-Item -ItemType Directory -Force "$layout\Assets" | Out-Null
Get-ChildItem assets -Filter *.png | Copy-Item -Destination "$layout\Assets" -Force

$manifest = Get-Content AppxManifest.xml -Raw -Encoding UTF8
if ($IdentityName) {
    $manifest = $manifest -replace '(<Identity[^>]*?Name=")[^"]*(")', "`${1}$IdentityName`${2}"
}
if ($Publisher) {
    $manifest = $manifest -replace '(<Identity[^>]*?Publisher=")[^"]*(")', "`${1}$Publisher`${2}"
}
if ($PublisherDisplayName) {
    $manifest = $manifest -replace '(<PublisherDisplayName>)[^<]*(</PublisherDisplayName>)', "`${1}$PublisherDisplayName`${2}"
}
if ($SelfSignTest) {
    # il Publisher del manifest deve coincidere con il Subject del certificato
    if ($manifest -notmatch '<Identity[^>]*?Publisher="([^"]*)"') { throw "Publisher non trovato nel manifest" }
    $subject = $Matches[1]
    if ($subject -match '00000000-0000') { $subject = "CN=MarkItDownApp Test"; 
        $manifest = $manifest -replace '(<Identity[^>]*?Publisher=")[^"]*(")', "`${1}$subject`${2}" }
}
if ($Version) {
    $manifest = $manifest -replace '(<Identity[^>]*?Version=")[^"]*(")', "`${1}$Version`${2}"
}
Set-Content "$layout\AppxManifest.xml" $manifest -Encoding UTF8
if ($manifest -match 'PUBLISHER\.MarkItDownApp|00000000-0000-0000-0000-000000000000') {
    Write-Warning "AppxManifest.xml contiene ancora Identity/Publisher segnaposto: sostituiscili con quelli di Partner Center prima di caricare lo Store."
}

# Pacchetto
$out = "dist\MarkItDownApp.msix"
New-Item -ItemType Directory -Force dist | Out-Null
if (Test-Path $out) { Remove-Item $out -Force }
& $makeappx pack /d $layout /p $out /o
if ($LASTEXITCODE -ne 0) { throw "makeappx fallito" }

# Firma di test con certificato autofirmato
if ($SelfSignTest -and -not $PfxPath) {
    $pfxSecure = ConvertTo-SecureString "test" -AsPlainText -Force
    $cert = New-SelfSignedCertificate -Type Custom -Subject $subject -KeyUsage DigitalSignature `
        -FriendlyName "MarkItDownApp test" -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
    $PfxPath = "dist\MarkItDownTest.pfx"; $PfxPassword = "test"
    Export-PfxCertificate -Cert $cert -FilePath $PfxPath -Password $pfxSecure | Out-Null
    Export-Certificate -Cert $cert -FilePath "dist\MarkItDownTest.cer" | Out-Null
    Remove-Item "Cert:\CurrentUser\My\$($cert.Thumbprint)" -Force
}
# Firma (test locale)
if ($PfxPath) {
    $signtool = Find-SdkTool "signtool.exe"
    if (-not $signtool) { throw "signtool.exe non trovato" }
    & $signtool sign /fd SHA256 /a /f $PfxPath /p $PfxPassword $out
    if ($LASTEXITCODE -ne 0) { throw "signtool fallito" }
}
Write-Host "`nOK -> $out"
