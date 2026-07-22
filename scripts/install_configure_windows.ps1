param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ask-YesNo([string]$Question, [bool]$DefaultYes = $true) {
    $hint = if ($DefaultYes) { "Y/n" } else { "y/N" }
    while ($true) {
        $answer = Read-Host "$Question [$hint]"
        if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
        $normalized = $answer.Trim().ToLowerInvariant()
        if ($normalized -eq "y" -or $normalized -eq "yes") { return $true }
        if ($normalized -eq "n" -or $normalized -eq "no") { return $false }
        Write-Host "Please answer yes or no."
    }
}

function Ask-PositiveInt([string]$Question, [int]$DefaultValue, [int]$MinValue = 256) {
    while ($true) {
        $answer = Read-Host "$Question [default $DefaultValue]"
        if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultValue }
        $parsed = 0
        if (-not [int]::TryParse($answer, [ref]$parsed)) {
            Write-Host "Please enter a number."
            continue
        }
        if ($parsed -lt $MinValue) {
            Write-Host "Value must be at least $MinValue."
            continue
        }
        return $parsed
    }
}

function Ask-ModelName {
    $models = @(
        "llama3.1:8b",
        "llama3.1:70b",
        "qwen2.5:7b",
        "mistral:7b"
    )
    Write-Host "Choose model to configure:"
    for ($i = 0; $i -lt $models.Count; $i++) {
        Write-Host ("  {0}. {1}" -f ($i + 1), $models[$i])
    }
    Write-Host ("  {0}. Manual model name" -f ($models.Count + 1))
    while ($true) {
        $choice = Read-Host ("Select number [default 1] (1-{0})" -f ($models.Count + 1))
        if ([string]::IsNullOrWhiteSpace($choice)) { return $models[0] }
        $index = 0
        if (-not [int]::TryParse($choice, [ref]$index)) {
            Write-Host "Please enter a number."
            continue
        }
        if ($index -ge 1 -and $index -le $models.Count) { return $models[$index - 1] }
        if ($index -eq ($models.Count + 1)) {
            $manual = Read-Host "Enter model name (example: llama3.1:8b)"
            if ([string]::IsNullOrWhiteSpace($manual)) {
                Write-Host "Model name cannot be blank."
                continue
            }
            return $manual.Trim()
        }
        Write-Host ("Please choose a number between 1 and {0}." -f ($models.Count + 1))
    }
}

function Ensure-Installed([string]$CommandName, [string]$WingetId, [string]$DisplayName) {
    if (Get-Command $CommandName -ErrorAction SilentlyContinue) {
        Write-Host "$DisplayName already installed."
        return
    }
    if (-not (Ask-YesNo "Install $DisplayName with winget?" $true)) {
        throw "$DisplayName is required to continue."
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required to install $DisplayName automatically."
    }
    winget install --id $WingetId --exact --accept-source-agreements --accept-package-agreements
}

function Get-PythonCommand {
    if (Get-Command python -ErrorAction SilentlyContinue) { return "python" }
    if (Get-Command py -ErrorAction SilentlyContinue) { return "py -3" }
    throw "Python command not found after installation."
}

Write-Step "Preparing fresh-system setup for Ollama tool runtime"

if (-not (Test-Path (Join-Path $RepoRoot "main.py"))) {
    throw "Expected main.py in repository root. Current RepoRoot: $RepoRoot"
}

Ensure-Installed -CommandName "git" -WingetId "Git.Git" -DisplayName "Git"
Ensure-Installed -CommandName "python" -WingetId "Python.Python.3.12" -DisplayName "Python"
Ensure-Installed -CommandName "ollama" -WingetId "Ollama.Ollama" -DisplayName "Ollama"

$pythonCmd = Get-PythonCommand

Write-Step "Installing runtime dependencies"
Push-Location $RepoRoot
try {
    $installVoiceDeps = Ask-YesNo "Install optional voice dependencies (pyttsx3, SpeechRecognition, pyaudio)?" $false
    if ($installVoiceDeps) {
        Invoke-Expression "$pythonCmd -m pip install --upgrade pip"
        Invoke-Expression "$pythonCmd -m pip install pyttsx3 SpeechRecognition pyaudio"
    }
} finally {
    Pop-Location
}

Write-Step "Configuring model and runtime settings"
$modelName = Ask-ModelName
$contextWindow = Ask-PositiveInt -Question "Context window size (tokens)" -DefaultValue 8192 -MinValue 256
$enableVoice = Ask-YesNo "Enable voice in GUI by default?" $true
$speakReplies = $false
if ($enableVoice) {
    $speakReplies = Ask-YesNo "Speak assistant replies by default?" $false
}

if (Ask-YesNo "Pull model '$modelName' now?" $true) {
    ollama pull $modelName
}

$settingsDir = Join-Path $RepoRoot ".runtime"
if (-not (Test-Path $settingsDir)) {
    New-Item -ItemType Directory -Path $settingsDir | Out-Null
}
$settingsPath = Join-Path $settingsDir "settings.json"
$settingsObject = [ordered]@{
    version = 1
    enable_voice_in_gui = $enableVoice
    speak_replies_by_default = $speakReplies
    default_model = $modelName
    context_window_tokens = $contextWindow
}
$settingsObject | ConvertTo-Json | Set-Content -Path $settingsPath -Encoding UTF8
Write-Host "Saved settings to $settingsPath"

Write-Step "Starting Ollama service process"
if (-not (Get-Process -Name "ollama" -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Step "Running tests"
Push-Location $RepoRoot
try {
    & $env:ComSpec /c "$pythonCmd -m unittest discover -s tests"
} finally {
    Pop-Location
}

if (Ask-YesNo "Launch GUI now?" $true) {
    Push-Location $RepoRoot
    try {
        $noVoiceArg = if ($enableVoice) { "" } else { " --no-voice" }
        & $env:ComSpec /c "$pythonCmd main.py gui --model $modelName --context-window $contextWindow$noVoiceArg"
    } finally {
        Pop-Location
    }
}

Write-Step "Setup complete"
Write-Host "You can rerun this script anytime to reconfigure model/context/settings."
