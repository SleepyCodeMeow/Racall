param([string]$Compiler)
# Tests only our language helper (no installation commands). Never installs Racall or touches a user profile.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
if (!$Compiler) {
    $Compiler = Get-ChildItem -LiteralPath "$env:LOCALAPPDATA/electron-builder/Cache" -Filter makensis.exe -Recurse |
        Where-Object FullName -Match '[\\/]Bin[\\/]makensis.exe$' |
        Select-Object -First 1 -ExpandProperty FullName
}
if (!$Compiler) { throw 'Build the Windows package first to populate the NSIS compiler cache.' }
$output = Join-Path $repoRoot 'test-results/installer-ui'
New-Item -ItemType Directory -Force -Path $output | Out-Null
& $Compiler /V2 "/DPROJECT_DIR=$repoRoot" "$repoRoot/installer/welcome-ui.nsi"
if ($LASTEXITCODE) { throw 'Native installer fixture compilation failed.' }
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Text;
using System.Runtime.InteropServices;
public static class InstallerUI {
    public delegate bool EnumCallback(IntPtr hwnd, IntPtr param);
    [DllImport("user32.dll")] static extern bool EnumWindows(EnumCallback fn, IntPtr param);
    [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr parent, EnumCallback fn, IntPtr param);
    [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint process);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, EntryPoint="SendMessageW")]
    public static extern IntPtr Send(IntPtr h, uint m, IntPtr w, IntPtr l);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, EntryPoint="SendMessageW")]
    public static extern IntPtr TextMessage(IntPtr h, uint m, IntPtr w, string s);
    [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int command);
    [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
    [DllImport("user32.dll")] public static extern bool RedrawWindow(IntPtr h, IntPtr rect, IntPtr region, uint flags);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int left, top, right, bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect rect);
    public static IntPtr Find(int pid) {
        IntPtr result=IntPtr.Zero;
        EnumWindows((h,p) => { uint id; GetWindowThreadProcessId(h,out id);
            if(id==pid && Class(h)=="#32770") {result=h; return false;} return true; },IntPtr.Zero);
        return result;
    }
    public static IntPtr[] Children(IntPtr h) {
        var items=new List<IntPtr>();
        EnumChildWindows(h,(c,p)=>{items.Add(c);return true;},IntPtr.Zero);
        return items.ToArray();
    }
    public static string Text(IntPtr h) {var s=new StringBuilder(2048);GetWindowText(h,s,s.Capacity);return s.ToString();}
    public static string Class(IntPtr h) {var s=new StringBuilder(128);GetClassName(h,s,s.Capacity);return s.ToString();}
    public static void Select(IntPtr list,int index) {
        Send(list,0x14E,(IntPtr)index,IntPtr.Zero);
        Send(GetParent(list),0x111,(IntPtr)(GetDlgCtrlID(list)|(1<<16)),list);
    }

}
"@
function Capture-Window([IntPtr]$window, [string]$path) {
    Start-Sleep -Milliseconds 300 # Let native combo selection/theme animations finish.
    [InstallerUI]::RedrawWindow($window, [IntPtr]::Zero, [IntPtr]::Zero, 0x185) | Out-Null
    $rect = New-Object InstallerUI+Rect
    if (![InstallerUI]::GetWindowRect($window, [ref]$rect)) { throw 'Window bounds unavailable' }
    $bitmap = New-Object System.Drawing.Bitmap(($rect.right-$rect.left), ($rect.bottom-$rect.top))
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $dc = $graphics.GetHdc()
        try { $ok = [InstallerUI]::PrintWindow($window, $dc, 2) } finally { $graphics.ReleaseHdc($dc) }
        if (!$ok) { throw 'PrintWindow failed' }
        $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    } finally { $graphics.Dispose(); $bitmap.Dispose() }
}
function Assert-UI($condition, [string]$message) { if (!$condition) { throw $message } }
function Count-Languages { return [InstallerUI]::Send($list, 0x146, 0, 0).ToInt32() }
$selectionFile = Join-Path $output ('selection-' + [guid]::NewGuid().ToString() + '.ini')
$chosenPath = Join-Path $output 'chosen folder/Racall'
$fixture = Start-Process -FilePath "$repoRoot/build/racall-installer-welcome.exe" -ArgumentList @('/REQUIRED=524288', "/RESULT=`"$selectionFile`"", "/D=$chosenPath") -WindowStyle Hidden -PassThru
try {
    $window = [IntPtr]::Zero
    for ($attempt=0; $attempt -lt 100; $attempt++) {
        $window = [InstallerUI]::Find($fixture.Id)
        if ($window -ne [IntPtr]::Zero) {
            $controls = [InstallerUI]::Children($window)
            $list = $controls | Where-Object { [InstallerUI]::Class($_) -eq 'ComboBox' } | Select-Object -First 1
            if ($list -and (Count-Languages) -eq 2) { break }
        }
        Start-Sleep -Milliseconds 100
    }
    Assert-UI ($list) 'Language controls missing'
    [InstallerUI]::ShowWindow($window, 4) | Out-Null
    Start-Sleep -Milliseconds 200
    $install = [InstallerUI]::GetDlgItem($window, 1)
    Assert-UI ((Count-Languages) -eq 2) 'Initial language count'
    Assert-UI ([InstallerUI]::Send($list,0x147,0,0).ToInt32() -eq 0) 'English must be selected'
    Assert-UI ([InstallerUI]::Text($window) -eq 'Racall Setup') 'English must be the default UI'
    Assert-UI ([InstallerUI]::IsWindowEnabled($install)) 'Install must initially be enabled'
    Assert-UI (!($controls | Where-Object { [InstallerUI]::Class($_) -in @('Edit','ListBox') })) 'No separate search or list'
    Capture-Window $window "$output/english.png"
    [InstallerUI]::Send($list,0x14F,1,0) | Out-Null
    Assert-UI ([InstallerUI]::Send($list,0x157,0,0).ToInt32() -eq 1) 'Dropdown must open'
    [InstallerUI]::Send($list,0x14F,0,0) | Out-Null
    [InstallerUI]::Select($list,1)
    Assert-UI ([InstallerUI]::Send($list,0x147,0,0).ToInt32() -eq 1) 'Russian must be selected'
    Assert-UI ([InstallerUI]::Text($window) -eq 'Установка Racall') 'Russian must apply immediately'
    Assert-UI ([InstallerUI]::Text($install) -match 'Установить') 'Translated install button'
    Assert-UI ([InstallerUI]::IsWindowEnabled($install)) 'Install remains enabled'
    Capture-Window $window "$output/russian.png"
    [InstallerUI]::Select($list,0)
    Assert-UI ([InstallerUI]::Text($window) -eq 'Racall Setup') 'Switching back to English'
    [InstallerUI]::Select($list,1)
    [InstallerUI]::Send($install,0xF5,0,0) | Out-Null
    Assert-UI ($fixture.WaitForExit(5000)) 'Helper must return after Install'
    Assert-UI ($fixture.ExitCode -eq 0) 'Successful selection exit code'
    $selection = Get-Content -LiteralPath $selectionFile -Raw
    Assert-UI ($selection -match 'language=1049') 'Selected Russian must reach parent'
    Assert-UI ($selection.Contains("directory=$chosenPath")) 'Chosen path with spaces must reach parent'
    Assert-UI (!(Test-Path -LiteralPath $chosenPath)) 'Helper must not install files'
    @{passed=$true; checks=@('English default','Native dropdown opens','Immediate translation','No separate search or list','Language and path handoff'); fixture='Production language helper, test size 512 MiB'} |
        ConvertTo-Json | Set-Content -Encoding utf8 "$output/result.json"
    Get-Content "$output/result.json"
} finally {
    if (!$fixture.HasExited) { Stop-Process -Id $fixture.Id -Force }
}

