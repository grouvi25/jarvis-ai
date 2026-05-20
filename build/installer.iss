; Inno Setup script для J.A.R.V.I.S.
; Сборка: ISCC.exe build\installer.iss
; После сборки появится файл `dist/Jarvis-Setup.exe`.

#define MyAppName       "Jarvis"
#define MyAppVersion    "0.2.0"
#define MyAppPublisher  "Jarvis"
#define MyAppURL        "https://github.com/grouvi25/jarvis-ai"
#define MyAppExeName    "Jarvis.exe"

[Setup]
AppId={{8B6F2DEE-9C04-4B12-9A4A-46C0F5C03B11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Jarvis-Setup
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\jarvis\assets\icon.ico

[Languages]
Name: "russian";  MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";  Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"
Name: "startupicon"; Description: "Запускать при старте Windows"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Если в будущем добавим доп. ресурсы рядом с exe:
; Source: "..\dist\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Открыть чат J.A.R.V.I.S."; Filename: "http://127.0.0.1:8765"
Name: "{group}\Удалить J.A.R.V.I.S."; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName} сейчас"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\Jarvis"
Type: filesandordirs; Name: "{localappdata}\Jarvis"
