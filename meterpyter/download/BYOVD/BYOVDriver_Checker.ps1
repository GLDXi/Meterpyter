# BYOVD - Check for vulnerable driver# BYOVD - Check for vulnerable driver
# Resource : 
# - https://gist.github.com/api0cradle/d52832e36aaf86d443b3b9f58d20c01d
# - https://blog.quarkslab.com/exploiting-lenovo-driver-cve-2025-8061.html
# - https://www.loldrivers.io/

Write-Host "+-------------+" -ForegroundColor White
Write-Host "|BYOVD Checker|" -ForegroundColor White 
Write-Host "+-------------+" -ForegroundColor White

$BarVert = [char]0x2502
$TeeBar = [char]0x251C
$Elbow = [char]0x2514
$Line = [char]0x2500

Write-Host "[*] Getting system drivers list..."


$CPath = "C:\Windows\System32\drivers\"
$drivers_from_C = Get-ChildItem -Path "$CPath"

Write-Host "[*] Getting known vulnerable drivers list...`n"

$web_client = New-Object System.Net.WebClient
$VulnerableDriversJson = $web_client.DownloadString("https://www.loldrivers.io/api/drivers.json")
$VulnerableDriversJson = $VulnerableDriversJson -replace '"INIT"', '"init"'
$VulnerableDrivers = $VulnerableDriversJson | ConvertFrom-Json

$VulnerableDriversFound = @()

Write-Host "[*] Checking $($drivers_from_C.Count) drivers against $($VulnerableDrivers.Count) known vulnerable drivers..." 
foreach ($VulnerableDriver in $VulnerableDrivers.KnownVulnerableSamples) {
    if ($drivers_from_C.Name -contains $VulnerableDriver.Filename) {
        $VulnerableDriversFound += $VulnerableDriver.Filename

        Write-Host " $TeeBar$Line" -NoNewline
        Write-Host "[x] " -NoNewline -ForegroundColor Red
        Write-host "Potentially vulnerable driver : $($VulnerableDriver.Filename)" 

        $Hash = Get-FileHash -Path "$CPath$($VulnerableDriver.Filename)"
        Write-Host " $BarVert  $TeeBar$Line[*] CPath Hash : $($Hash.Hash.ToLower())"
        Write-Host " $BarVert  $Elbow$Line[*] KDriv Hash : $($VulnerableDriver.Sha256)"

        if ($VulnerableDriver.Sha256 -eq $Hash.Hash){
            Write-Host " $BarVert     $Elbow$Line" -NoNewline
            Write-Host "[!] " -NoNewline -ForegroundColor Red
            Write-Host "Verified vulnerable driver $($VulnerableDriver.Filename) (Matching SHA256)" 
        } else {
            Write-Host " $BarVert     $Elbow$Line" -NoNewline
            Write-host "[+] " -NoNewline -ForegroundColor Green
            Write-host "Not Vulnerable (Matching SHA256)" 
        }
    }
}
Write-Host " $BarVert"
Write-Host " $Elbow$Line[*] Checkup complete"



    <#foreach ($driver in $drivers) {
        $line = "[*] Checking $($driver.Name)..."
        Write-host $line -NoNewline -ForegroundColor Yellow
        Start-Sleep -Milliseconds 10
        if ($driver.Name -contains $VulnerableDriver.Filename) {
            Write-Host "Test`n" -ForegroundColor Red

        } else {
            Write-Host ("`r" + (' ' * $line.Length) + "`r") -NoNewline
        }
    }#>

Write-Host "`n"