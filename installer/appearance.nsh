; Keep native Windows chrome and a light Racall-branded content area.
!include LogicLib.nsh
!define MUI_CUSTOMFUNCTION_GUIINIT RacallInitializeWindow
; Header/finish bitmaps are configured through electron-builder in package.json.
!define MUI_BGCOLOR "FFFFFF"
!define MUI_TEXTCOLOR "242424"
!define MUI_INSTFILESPAGE_COLORS "242424 FFFFFF"

!macro customHeader
  Caption "$(Racall_setup)"
  BrandingText " "
  SetFont "Segoe UI" 9
!macroend

; Let DWM draw native caption colors. Never override the user's theme or draw custom chrome.
; Apply the current app-theme preference on opening; unsupported DWM versions keep defaults.
Function RacallInitializeWindow
  Push $0
  Push $1
  StrCpy $1 0
  ReadRegDWORD $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" "AppsUseLightTheme"
  ${If} $0 == 0
    StrCpy $1 1
  ${EndIf}
  System::Call 'dwmapi::DwmSetWindowAttribute(p $HWNDPARENT, i 20, *i r1, i 4)'
  Pop $1
  Pop $0
FunctionEnd
