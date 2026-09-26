; Shared production/preview installation layout. Native status and progress
; handles stay intact so the installer engine continues to report real work.
!include "${PROJECT_DIR}\installer\layout.nsh"
!insertmacro MUI_INSTFILESPAGE_INTERFACE
Var RacallProgressTitle
Var RacallProgressIntro
Var RacallProgressActivity
Var RacallProgressLogo
Var RacallProgressBitmap
Var RacallProgressDivider

!macro RacallProgressLabel HANDLE ID TEXT
  System::Call 'user32::CreateWindowExW(i 0, w "STATIC", w "${TEXT}", i 0x50000080, i 0, i 0, i 1, i 1, p $mui.InstFilesPage, p ${ID}, p 0, p 0) p.s'
  Pop ${HANDLE}
  SetCtlColors ${HANDLE} 000000 FFFFFF
  SendMessage ${HANDLE} ${WM_SETFONT} $RacallBodyFont 1
!macroend

Function RacallProgressShow
  !insertmacro RacallSizeWindow
  !insertmacro RacallCreateFonts
  SetCtlColors $HWNDPARENT 000000 F0F0F0
  SetCtlColors $mui.InstFilesPage 000000 FFFFFF
  ; The full-height white page replaces MUI's separate header and details panel.
  System::Call 'user32::GetWindow(p $HWNDPARENT, i 5) p.r4'
  ${DoWhile} $4 != 0
    ${If} $4 != $mui.InstFilesPage
    ${AndIf} $4 != $mui.Button.Cancel
      ShowWindow $4 ${SW_HIDE}
    ${EndIf}
    System::Call 'user32::GetWindow(p r4, i 2) p.r4'
  ${Loop}
  ShowWindow $mui.InstFilesPage.ShowLogButton ${SW_HIDE}
  ShowWindow $mui.InstFilesPage.Log ${SW_HIDE}
  !insertmacro RacallProgressLabel $RacallProgressTitle 2101 "$(Racall_progressTitle)"
  !insertmacro RacallProgressLabel $RacallProgressIntro 2102 "$(Racall_progressIntro)"
  !insertmacro RacallProgressLabel $RacallProgressActivity 2103 "$(Racall_progressActivity)"
  SendMessage $RacallProgressTitle ${WM_SETFONT} $RacallTitleFont 1
  SetCtlColors $mui.InstFilesPage.Text 000000 FFFFFF
  SendMessage $mui.InstFilesPage.Text ${WM_SETFONT} $RacallBodyFont 1
  ; Long engine messages/paths stay on one line; no clipping outside the page.
  System::Call 'user32::GetWindowLongW(p $mui.InstFilesPage.Text, i -16) i.r0'
  IntOp $0 $0 | 0x8080 ; SS_PATHELLIPSIS | SS_NOPREFIX
  System::Call 'user32::SetWindowLongW(p $mui.InstFilesPage.Text, i -16, i r0)'
  ; The engine may replace this with a status message. Otherwise show the real
  ; destination, not a fabricated per-file name (the 7z backend exposes bytes).
  SendMessage $mui.InstFilesPage.Text ${WM_SETTEXT} 0 'STR:$INSTDIR'
  System::Call 'user32::CreateWindowExW(i 0, w "STATIC", w "", i 0x5000000E, i 0, i 0, i 1, i 1, p $mui.InstFilesPage, p 2104, p 0, p 0) p.s'
  Pop $RacallProgressLogo
  System::Call 'user32::CreateWindowExW(i 0, w "STATIC", w "", i 0x50000000, i 0, i 0, i 1, i 1, p $HWNDPARENT, p 2105, p 0, p 0) p.s'
  Pop $RacallProgressDivider
  SetCtlColors $RacallProgressDivider A0A0A0 A0A0A0
  !insertmacro RacallPlace $mui.InstFilesPage 0 0 835 542
  !insertmacro RacallPlace $RacallProgressTitle 34 11 600 24
  !insertmacro RacallPlace $RacallProgressIntro 56 37 724 22
  !insertmacro RacallPlace $RacallProgressLogo 612 8 221 84
  !insertmacro RacallPlace $RacallProgressActivity 56 101 724 22
  !insertmacro RacallPlace $mui.InstFilesPage.Text 56 123 724 22
  !insertmacro RacallPlace $mui.InstFilesPage.ProgressBar 56 161 724 28
  !insertmacro RacallPlace $RacallProgressDivider 0 541 835 1
  !insertmacro RacallPlace $mui.Button.Cancel 717 560 103 30
  SendMessage $mui.Button.Cancel ${WM_SETFONT} $RacallBodyFont 1
  InitPluginsDir
  File /oname=$PLUGINSDIR\progress-logo.bmp "${PROJECT_DIR}\installer\assets\welcome.bmp"
  ${NSD_SetStretchedImage} $RacallProgressLogo "$PLUGINSDIR\progress-logo.bmp" $RacallProgressBitmap
FunctionEnd


Function RacallProgressComplete
  ; Keep the native failure page dismissible even though Next is hidden while
  ; extracting. Successful installs close automatically in the production flow.
  IfAbort 0 racall_progress_done
    SendMessage $RacallProgressTitle ${WM_SETTEXT} 0 'STR:$(MUI_TEXT_ABORT_TITLE)'
    SendMessage $RacallProgressIntro ${WM_SETTEXT} 0 'STR:$(MUI_TEXT_ABORT_SUBTITLE)'
    ShowWindow $RacallProgressActivity ${SW_HIDE}
    ShowWindow $mui.Button.Next ${SW_HIDE}
    ShowWindow $mui.Button.Cancel ${SW_SHOW}
    EnableWindow $mui.Button.Cancel 1
    SendMessage $mui.Button.Cancel ${WM_SETTEXT} 0 'STR:$(^CloseBtn)'
  racall_progress_done:
FunctionEnd
