; Run the small first screen before NSIS freezes its language table after .onInit.
; The helper writes only to this process's temporary plugin directory.
!ifndef BUILD_UNINSTALLER
  !system '"${NSISDIR}\Bin\makensis.exe" /V2 /DPROJECT_DIR="${PROJECT_DIR}" "${PROJECT_DIR}\installer\welcome-ui.nsi"' = 0
!endif
!macro customInit
  ${IfNot} ${Silent}
    InitPluginsDir
    File /oname=$PLUGINSDIR\racall-welcome.exe "${PROJECT_DIR}\build\racall-installer-welcome.exe"
    SectionGetSize 0 $R2
    ExecWait '"$PLUGINSDIR\racall-welcome.exe" /LANGUAGE=$LANGUAGE /REQUIRED=$R2 /RESULT="$PLUGINSDIR\selection.ini" /D=$INSTDIR' $R2
    ${If} $R2 != 0
      Quit
    ${EndIf}
    ReadINIStr $R1 "$PLUGINSDIR\selection.ini" "selection" "language"
    !insertmacro RacallEachLanguage RacallAcceptCommandLanguage
    ReadINIStr $R2 "$PLUGINSDIR\selection.ini" "selection" "directory"
    ${If} $R2 == ""
      Quit
    ${EndIf}
    StrCpy $INSTDIR $R2
  ${EndIf}
!macroend
!macro customInstallMode
  ; Preserve the chosen path; the standard current-user macro would reset it.
  !ifndef BUILD_UNINSTALLER
    ${If} $installMode == "CurrentUser"
      Abort
    ${EndIf}
  !endif
!macroend
