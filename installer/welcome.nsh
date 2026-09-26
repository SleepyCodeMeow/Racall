; Searchable first page. Only data/filtering and presentation live here.
!include nsDialogs.nsh
!include LogicLib.nsh
!include WinMessages.nsh

!macro RacallAddLanguage LOCALE ID NAME SEARCH
  System::Call 'shlwapi::StrStrIW(w "${SEARCH}", w "$RacallQuery") p.r0'
  ${If} $RacallQuery == ""
  ${OrIf} $0 != 0
    SendMessage $RacallList ${LB_ADDSTRING} 0 'STR:${NAME}' $1
    SendMessage $RacallList ${LB_SETITEMDATA} $1 ${ID}
    ${If} $LANGUAGE == ${ID}
      SendMessage $RacallList ${LB_SETCURSEL} $1 0
    ${EndIf}
  ${EndIf}
!macroend

!macro RacallWelcomePage
  !insertmacro RacallTextVariables
  !insertmacro MUI_PAGE_INIT
  Page custom RacallWelcome RacallWelcomeLeave

  Var RacallPage
  Var RacallIntro
  Var RacallLabel
  Var RacallSearch
  Var RacallList
  Var RacallHint
  Var RacallFolderButton
  Var RacallFolderLabel
  Var RacallSpace
  Var RacallNext
  Var RacallQuery
  Var RacallRequiredMB
  Var RacallAvailableMB

  Function RacallWelcome
    nsDialogs::Create 1018
    Pop $RacallPage
    ${If} $RacallPage == error
      Abort
    ${EndIf}
    SetCtlColors $HWNDPARENT 242424 FFFFFF
    SetCtlColors $RacallPage 242424 FFFFFF
    GetDlgItem $RacallNext $HWNDPARENT 1
    GetDlgItem $0 $HWNDPARENT 3
    ShowWindow $0 ${SW_HIDE}

    ${NSD_CreateLabel} 0 0 100% 25u ""
    Pop $RacallIntro
    SetCtlColors $RacallIntro 242424 FFFFFF
    ${NSD_CreateLabel} 0 30u 100% 12u ""
    Pop $RacallLabel
    SetCtlColors $RacallLabel 242424 FFFFFF
    ${NSD_CreateText} 0 45u 185u 14u ""
    Pop $RacallSearch
    ${NSD_OnChange} $RacallSearch RacallSearchChanged
    ${NSD_CreateListBox} 0 63u 185u 43u ""
    Pop $RacallList
    ${NSD_OnChange} $RacallList RacallLanguageChanged
    ${NSD_CreateLabel} 0 108u 200u 15u ""
    Pop $RacallHint
    SetCtlColors $RacallHint 606060 FFFFFF
    ${NSD_CreateButton} 205u 45u 95u 16u ""
    Pop $RacallFolderButton
    ${NSD_OnClick} $RacallFolderButton RacallChooseFolder
    ${NSD_CreateLabel} 205u 67u 95u 50u ""
    Pop $RacallFolderLabel
    SetCtlColors $RacallFolderLabel 606060 FFFFFF
    ${NSD_CreateLabel} 0 127u 100% 13u ""
    Pop $RacallSpace
    SetCtlColors $RacallSpace 606060 FFFFFF
    StrCpy $RacallQuery ""
    Call RacallRefreshText
    Call RacallFilter
    Call RacallDiskSpace
    ${NSD_SetFocus} $RacallSearch
    nsDialogs::Show
  FunctionEnd

  Function RacallRefreshText
    !insertmacro RacallLoadText
    !insertmacro MUI_HEADER_TEXT "Racall" ""
    SendMessage $HWNDPARENT ${WM_SETTEXT} 0 'STR:$RacallText_setup'
    ${NSD_SetText} $RacallIntro "$RacallText_intro"
    ${NSD_SetText} $RacallLabel "$RacallText_language"
    ${NSD_Edit_SetCueBannerText} $RacallSearch 1 "$RacallText_search"
    ${NSD_SetText} $RacallFolderButton "$RacallText_folder"
    ${NSD_SetText} $RacallNext "$RacallText_install"
    GetDlgItem $0 $HWNDPARENT 2
    ${NSD_SetText} $0 "$RacallText_cancel"
  FunctionEnd

  Function RacallSearchChanged
    Pop $0
    ${NSD_GetText} $RacallSearch $RacallQuery
    Call RacallFilter
  FunctionEnd

  Function RacallFilter
    SendMessage $RacallList ${LB_RESETCONTENT} 0 0
    !insertmacro RacallEachLanguage RacallAddLanguage
    Call RacallSelectionState
  FunctionEnd

  Function RacallSelectionState
    SendMessage $RacallList ${LB_GETCURSEL} 0 0 $0
    ${If} $0 == -1
      EnableWindow $RacallNext 0
      SendMessage $RacallList ${LB_GETCOUNT} 0 0 $0
      ${If} $0 == 0
        ${NSD_SetText} $RacallHint "$RacallText_empty"
      ${Else}
        ${NSD_SetText} $RacallHint "$RacallText_choose"
      ${EndIf}
    ${Else}
      EnableWindow $RacallNext 1
      ${NSD_SetText} $RacallHint ""
      ${If} $RacallAvailableMB != -1
      ${AndIf} $RacallAvailableMB < $RacallRequiredMB
        EnableWindow $RacallNext 0
        ${NSD_SetText} $RacallHint "$RacallText_spaceError"
      ${EndIf}
    ${EndIf}
  FunctionEnd

  Function RacallLanguageChanged
    Pop $0
    SendMessage $RacallList ${LB_GETCURSEL} 0 0 $0
    ${If} $0 != -1
      SendMessage $RacallList ${LB_GETITEMDATA} $0 0 $1
      StrCpy $LANGUAGE $1
      Call RacallRefreshText
      Call RacallDiskSpace
    ${EndIf}
  FunctionEnd

  Function RacallChooseFolder
    Pop $0
    nsDialogs::SelectFolderDialog "$RacallText_folderTitle" "$INSTDIR"
    Pop $0
    ${If} $0 != error
    ${AndIf} $0 != ""
      ${GetFileName} $0 $1
      ${If} $1 == "Racall"
        StrCpy $INSTDIR $0
      ${Else}
        StrCpy $INSTDIR "$0\Racall"
      ${EndIf}
      ${NSD_SetText} $RacallFolderLabel "$INSTDIR"
      Call RacallDiskSpace
    ${EndIf}
  FunctionEnd

  Function RacallDiskSpace
    ; The parent passes the real unpacked section size, in KiB.
    StrCpy $RacallRequiredMB $RacallSectionKB
    IntOp $RacallRequiredMB $RacallRequiredMB + 1023
    IntOp $RacallRequiredMB $RacallRequiredMB / 1024
    ${GetRoot} "$INSTDIR" $0
    StrCpy $0 "$0\"
    System::Call 'kernel32::GetDiskFreeSpaceExW(w r0, *l .r1, p 0, p 0) i.r2'
    StrCpy $RacallAvailableMB -1
    ${If} $2 != 0
      System::Int64Op $1 / 1048576
      Pop $RacallAvailableMB
      ${NSD_SetText} $RacallSpace "$RacallText_required $RacallRequiredMB MB    $RacallText_available $RacallAvailableMB MB"
    ${Else}
      ${NSD_SetText} $RacallSpace "$RacallText_required $RacallRequiredMB MB    $RacallText_unavailable"
    ${EndIf}
    Call RacallSelectionState
  FunctionEnd

  Function RacallWelcomeLeave
    Call RacallDiskSpace
    SendMessage $RacallList ${LB_GETCURSEL} 0 0 $0
    ${If} $0 == -1
      Abort
    ${EndIf}
    ${If} $RacallAvailableMB != -1
    ${AndIf} $RacallAvailableMB < $RacallRequiredMB
      MessageBox MB_OK|MB_ICONEXCLAMATION "$RacallText_spaceError"
      Abort
    ${EndIf}
    Call RacallAccept
  FunctionEnd
!macroend
