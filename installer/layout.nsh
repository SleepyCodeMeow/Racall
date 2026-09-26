; Shrink only the helper's unused vertical space; keep Windows font/DPI scaling.
!macro RacallCompactLayout
  System::Call '*(i, i, i, i) p.r9'
  System::Call 'user32::GetWindowRect(p $RacallPage, p r9)'
  System::Call '*$9(i .r0, i .r1, i .r2, i .r3)'
  StrCpy $7 $3
  IntOp $8 $3 - $1
  IntOp $8 $8 * 2
  IntOp $8 $8 / 5
  ; Move the native footer controls up by the same amount as the window shrinks.
  System::Call 'user32::GetWindow(p $HWNDPARENT, i 5) p.r4'
  ${DoWhile} $4 != 0
    System::Call 'user32::GetWindowRect(p r4, p r9)'
    System::Call '*$9(i .r0, i .r1, i .r2, i .r3)'
    ${If} $1 >= $7
      System::Call 'user32::MapWindowPoints(p 0, p $HWNDPARENT, p r9, i 2)'
      System::Call '*$9(i .r0, i .r1, i .r2, i .r3)'
      IntOp $1 $1 - $8
      System::Call 'user32::SetWindowPos(p r4, p 0, i r0, i r1, i 0, i 0, i 5)'
    ${EndIf}
    System::Call 'user32::GetWindow(p r4, i 2) p.r4'
  ${Loop}
  System::Call 'user32::GetClientRect(p $RacallPage, p r9)'
  System::Call '*$9(i .r0, i .r1, i .r2, i .r3)'
  IntOp $3 $3 - $8
  System::Call 'user32::SetWindowPos(p $RacallPage, p 0, i 0, i 0, i r2, i r3, i 6)'
  System::Call 'user32::GetWindowRect(p $HWNDPARENT, p r9)'
  System::Call '*$9(i .r0, i .r1, i .r2, i .r3)'
  IntOp $2 $2 - $0
  IntOp $3 $3 - $1
  IntOp $3 $3 - $8
  System::Call 'user32::SetWindowPos(p $HWNDPARENT, p 0, i 0, i 0, i r2, i r3, i 6)'
  System::Free $9
!macroend
