; Standalone visual fixture: the real NSIS progress page, without any install payload.
; Do not include languages.nsh/selection.nsh: they contain production install hooks.
Unicode true
RequestExecutionLevel user
Name "Racall"
OutFile "${PROJECT_DIR}\build\Racall-progress-preview.exe"
!define MUI_ICON "${PROJECT_DIR}\assets\icon.ico"
!include MUI2.nsh
!include FileFunc.nsh
!include "${PROJECT_DIR}\installer\appearance.nsh"
!include "${PROJECT_DIR}\installer\catalog.nsh"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${PROJECT_DIR}\installer\assets\header.bmp"
!define MUI_CUSTOMFUNCTION_ABORT PreviewAbort
!define MUI_PAGE_CUSTOMFUNCTION_SHOW PreviewShow
!insertmacro MUI_PAGE_INSTFILES
!insertmacro RacallLoadLanguages
!insertmacro customHeader

ShowInstDetails nevershow
Var PreviewProgress
LangString PreviewExtract 1033 "Extracting: resources\app.asar (preview only)"
LangString PreviewExtract 1049 "Распаковка: resources\app.asar (только просмотр)"

Function .onInit
  StrCpy $LANGUAGE 1033
  ${GetParameters} $R0
  ${GetOptions} $R0 "/LANGUAGE=" $R1
  ${If} $R1 == "1049"
    StrCpy $LANGUAGE 1049
  ${EndIf}
FunctionEnd

Function PreviewShow
  SendMessage $HWNDPARENT ${WM_SETTEXT} 0 'STR:Preview - $(Racall_setup)'
  ; NSIS updates its own bar from instruction counts. Use an identical native
  ; control at the same bounds for the paused sample; keep the real bar hidden.
  System::Call '*(i 0, i 0, i 0, i 0) p.r8'
  System::Call 'user32::GetWindowRect(p $mui.InstFilesPage.ProgressBar, p r8)'
  System::Call 'user32::MapWindowPoints(p 0, p $mui.InstFilesPage, p r8, i 2)'
  System::Call '*$8(i .r0, i .r1, i .r2, i .r3)'
  System::Free $8
  IntOp $2 $2 - $0
  IntOp $3 $3 - $1
  System::Call 'user32::GetWindowLongW(p $mui.InstFilesPage.ProgressBar, i -16) i.r4'
  System::Call 'user32::GetWindowLongW(p $mui.InstFilesPage.ProgressBar, i -20) i.r5'
  System::Call 'user32::CreateWindowExW(i r5, w "msctls_progress32", w "", i r4, i r0, i r1, i r2, i r3, p $mui.InstFilesPage, p 2004, p 0, p 0) p.s'
  Pop $PreviewProgress
  ShowWindow $mui.InstFilesPage.ProgressBar ${SW_HIDE}
  SendMessage $PreviewProgress 0x406 0 100
  SendMessage $PreviewProgress 0x402 42 0
FunctionEnd

Function PreviewAbort
  ; Safe even during progress: this fixture only sleeps and updates controls.
  Quit
FunctionEnd

Section
  ; No File, registry, shortcut, profile, subprocess or installer commands here.
  ; Hold a sample progress position until the user closes the preview.
  GetDlgItem $1 $HWNDPARENT 2
  EnableWindow $1 1
  SetDetailsPrint textonly
  DetailPrint "$(PreviewExtract)"
  ${Do}
    Sleep 250
  ${Loop}
SectionEnd
