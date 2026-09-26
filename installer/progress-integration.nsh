; Hook only the actual installation page, after any scope/directory pages.
; Keep the standard extraction, upgrade, error and silent-install logic.
!ifndef BUILD_UNINSTALLER
  !include MUI2.nsh
  !include "${PROJECT_DIR}\installer\progress.nsh"
  !macro customPageAfterChangeDir
    !define MUI_PAGE_CUSTOMFUNCTION_SHOW RacallProgressShow
    !define MUI_PAGE_CUSTOMFUNCTION_LEAVE RacallProgressComplete
  !macroend

  ; Two-screen interactive flow: welcome, progress; then close and launch.
  !macro customFinishPage
    AutoCloseWindow true
    Function StartApp
      ${If} ${isUpdated}
        StrCpy $1 "--updated"
      ${Else}
        StrCpy $1 ""
      ${EndIf}
      ${StdUtils.ExecShellAsUser} $0 "$launchLink" "open" "$1"
    FunctionEnd
    Function .onInstSuccess
      !ifndef HIDE_RUN_AFTER_FINISH
        ${IfNot} ${Silent}
          Call StartApp
        ${EndIf}
      !endif
    FunctionEnd
  !macroend
!endif

