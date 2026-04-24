; Installer for DashAI (Windows). Based on PyInstaller one-dir portable executable
; ---------------------------------------------
; Command to generate the executable:
; pyinstaller -D -n DashAI-launcher-cpu --clean --add-data "DashAI/front/build;DashAI/front/build" --add-data "%CONDA_PREFIX%\Lib\site-packages\transformers;transformers" --add-binary "%CONDA_PREFIX%\Lib\site-packages\llama_cpp\lib\*;llama_cpp/lib" --additional-hooks-dir=hooks DashAI/__main__.py
[Setup]
AppName=DashAI
AppVersion=0.9.0
AppPublisher=DashAI Software
AppPublisherURL=https://dash-ai.com
DefaultDirName={pf}\DashAI
DefaultGroupName=DashAI
OutputDir=installer
OutputBaseFilename=DashAI-Installer
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=DashAI.ico

[Files]
; Copy all files from PyInstaller onedir output
Source: "dist\DashAI-launcher-cpu\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\DashAI"; Filename: "{app}\DashAI-launcher-cpu.exe"
Name: "{commondesktop}\DashAI"; Filename: "{app}\DashAI-launcher-cpu.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; Flags: unchecked

[Run]
Filename: "{app}\DashAI-launcher-cpu.exe"
Description: "Launch DashAI"
Flags: postinstall nowait skipifsilent
