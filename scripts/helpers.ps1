Remove-Item Alias:R -Force -ErrorAction SilentlyContinue
$script:U8 = New-Object System.Text.UTF8Encoding($false)
function W($File, $Content) {
  $p = Join-Path (Get-Location) $File
  New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
  [IO.File]::WriteAllText($p, $Content, $script:U8); Write-Host "OK W: $File" -ForegroundColor Green
}
function A($File, $Content) {
  $p = Join-Path (Get-Location) $File
  $old = if (Test-Path $p) { [IO.File]::ReadAllText($p) } else { "" }
  if ($old.Contains($Content.Trim())) { Write-Host "JA ADICIONADO: $File" -ForegroundColor Cyan; return }
  [IO.File]::WriteAllText($p, $old.TrimEnd() + "`n`n" + $Content.Trim() + "`n", $script:U8); Write-Host "OK A: $File" -ForegroundColor Green
}
function R($File, $Old, $New) {
  $p = Join-Path (Get-Location) $File
  $t = [IO.File]::ReadAllText($p)
  if (-not $t.Contains($Old)) { Write-Host "NAO ENCONTRADO/JA APLICADO: $File" -ForegroundColor Yellow; return }
  $i = $t.IndexOf($Old)
  [IO.File]::WriteAllText($p, $t.Substring(0,$i) + $New + $t.Substring($i + $Old.Length), $script:U8); Write-Host "OK R: $File" -ForegroundColor Green
}