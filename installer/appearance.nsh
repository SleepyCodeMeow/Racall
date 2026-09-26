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
  Push $2
  Push $3
  Push $4
  ; Preserve the client area of the standard progress/finish pages when changing frame style.
  System::Call "*(i 0, i 0, i 0, i 0) p.r4"
  System::Call "user32::GetClientRect(p $HWNDPARENT, p r4)"
  ; WS_THICKFRAME gives DWM the standard desktop caption metrics (31 px at 96 DPI).
  ; Keep the wizard fixed-size: remove Size from the system menu, including edge sizing.
  System::Call 'user32::GetWindowLongW(p $HWNDPARENT, i -16) i.r0'
  IntOp $0 $0 | 0x00040000
  System::Call 'user32::SetWindowLongW(p $HWNDPARENT, i -16, i r0)'
  System::Call 'user32::GetWindowLongW(p $HWNDPARENT, i -20) i.r1'
  System::Call 'user32::GetDpiForWindow(p $HWNDPARENT) i.r3'
  System::Call 'user32::AdjustWindowRectExForDpi(p r4, i r0, i 0, i r1, i r3) i.r2'
  ${If} $2 != 1
    System::Call 'user32::AdjustWindowRectEx(p r4, i r0, i 0, i r1)'
  ${EndIf}
  System::Call '*$4(i .r0, i .r1, i .r2, i .r3)'
  System::Free $4
  IntOp $2 $2 - $0
  IntOp $3 $3 - $1
  System::Call 'user32::SetWindowPos(p $HWNDPARENT, p 0, i 0, i 0, i r2, i r3, i 0x36)'
  System::Call 'user32::GetSystemMenu(p $HWNDPARENT, i 0) p.r0'
  System::Call 'user32::DeleteMenu(p r0, i 0xF000, i 0)'
  StrCpy $1 0
  ReadRegDWORD $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" "AppsUseLightTheme"
  ${If} $0 == 0
    StrCpy $1 1
  ${EndIf}
  System::Call 'dwmapi::DwmSetWindowAttribute(p $HWNDPARENT, i 20, *i r1, i 4)'
  Pop $4
  Pop $3
  Pop $2
  Pop $1
  Pop $0
FunctionEnd
