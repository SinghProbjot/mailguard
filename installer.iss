; MailGuard installer (Inno Setup 6). Build with build_setup.ps1
#define AppName "MailGuard"
#define AppVersion "1.0.0"
#define AppExe "MailGuard.exe"

[Setup]
AppId={{7E3F1C2A-5B64-4E0B-9D1A-2C8F4A6B9E10}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=MailGuard
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=dist
OutputBaseFilename=MailGuard-Setup-{#AppVersion}
SetupIconFile=mailguard\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible
ShowLanguageDialog=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"

[CustomMessages]
en.AutostartTask=Start {#AppName} when you sign in to Windows (recommended: protection starts on its own)
en.AutostartGroup=Autostart:
en.RemoveData=Also delete MailGuard settings and log (%1)?
en.AppComment=Local phishing protection for Outlook
it.AutostartTask=Avvia {#AppName} all'accesso a Windows (consigliato: la protezione parte da sola)
it.AutostartGroup=Avvio automatico:
it.RemoveData=Eliminare anche le impostazioni e il registro di MailGuard (%1)?
it.AppComment=Protezione anti-phishing locale per Outlook

[Tasks]
Name: "autostart"; Description: "{cm:AutostartTask}"; GroupDescription: "{cm:AutostartGroup}"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\MailGuard"; ValueType: string; ValueName: "Language"; ValueData: "{language}"; Flags: uninsdeletekey

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "{cm:AppComment}"
Name: "{autoprograms}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Parameters: "--tray"; Comment: "{cm:AppComment}"; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#AppExe} /F"; Flags: runhidden; RunOnceId: "KillMailGuard"

[UninstallDelete]
Type: filesandordirs; Name: "{userstartup}\{#AppName}.lnk"

[Code]
// Closes MailGuard if it is running before copying files
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  R: Integer;
begin
  Exec(ExpandConstant('{cmd}'), '/C taskkill /IM {#AppExe} /F', '', SW_HIDE, ewWaitUntilTerminated, R);
  Sleep(800);
  Result := '';
end;

// After uninstalling, asks whether to delete the data in %APPDATA%\MailGuard
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\{#AppName}');
    if DirExists(DataDir) then
      if MsgBox(FmtMessage(CustomMessage('RemoveData'), [DataDir]), mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;

