[Setup]
AppName=Minimalia
AppVersion=1.0.0
AppPublisher=Aniruddha Bose
AppPublisherURL=https://github.com/Aniruddha-Bose/Minimalia
DefaultDirName={autopf}\Minimalia
DefaultGroupName=Minimalia
UninstallDisplayIcon={app}\Minimalia.exe
OutputDir=installer_output
OutputBaseFilename=Minimalia_Setup
SetupIconFile=assets\ui\minimalia_appicon.ico
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
Source: "dist\Minimalia.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Minimalia"; Filename: "{app}\Minimalia.exe"
Name: "{group}\Uninstall Minimalia"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Minimalia"; Filename: "{app}\Minimalia.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\Minimalia.exe"; Description: "Launch Minimalia"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{userappdata}\Minimalia\browser_data"
Type: dirifempty; Name: "{userappdata}\Minimalia\browser_cache"
Type: files; Name: "{userappdata}\Minimalia\settings.json"
Type: dirifempty; Name: "{userappdata}\Minimalia"
