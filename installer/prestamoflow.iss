; Script del instalador de PrestamoFlow (Inno Setup 6).
; Requisito: tener el bundle compilado en backend\dist\PrestamoFlow
;   (ver README.md -> "Instalador .exe").
; Compilar con:  iscc.exe installer\prestamoflow.iss
;
; Nota: los datos (prestamos.db, .secret, backups) se guardan junto al
; ejecutable, por eso se instala en %LOCALAPPDATA% (escribible sin admin).

#define AppName "PrestamoFlow"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#define AppExeName "PrestamoFlow.exe"
#define BundleRoot "..\backend\dist\PrestamoFlow"

[Setup]
AppId={{7B5F4E2A-9C31-4D6B-8A2E-PRESTAMOFLOW1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=PrestamoFlow contributors
DefaultDirName={localappdata}\PrestamoFlow
DefaultGroupName={#AppName}
AllowNoIcons=yes
PrivilegesRequired=lowest
; Cierra PrestamoFlow automáticamente si está en ejecución durante
; la instalación o desinstalación (evita errores de archivos en uso).
CloseApplications=yes
CloseApplicationsFilter=*.exe
OutputDir=output
OutputBaseFilename=PrestamoFlow-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#BundleRoot}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#BundleRoot}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\prestamos.db"
Type: filesandordirs; Name: "{app}\.secret"
Type: filesandordirs; Name: "{app}\backups"

[Code]
procedure KillPrestamoFlow;
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /IM PrestamoFlow.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  KillPrestamoFlow;
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  KillPrestamoFlow;
  Result := True;
end;