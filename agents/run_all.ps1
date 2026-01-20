Write-Host "Starting Kompline agents..."

$commandOrchestrator = "python -m agents.run orchestrator"
$commandValidator = "python -m agents.run validator"
$commandReporter = "python -m agents.run reporter"

Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $commandOrchestrator
Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $commandValidator
Start-Process -WindowStyle Normal -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $commandReporter
