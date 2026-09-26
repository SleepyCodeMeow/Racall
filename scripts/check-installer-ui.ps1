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
$releaseLabel = (Get-Content -LiteralPath "$repoRoot/apps/shared/release.json" -Raw | ConvertFrom-Json).label
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
    [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h, int index);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out Rect rect);
    [DllImport("user32.dll")] public static extern IntPtr GetSystemMenu(IntPtr h, bool revert);
    [DllImport("user32.dll")] public static extern uint GetMenuState(IntPtr h, uint item, uint flags);
    [DllImport("user32.dll")] public static extern IntPtr SendMessageTimeout(IntPtr h, uint m, IntPtr w, IntPtr l, uint flags, uint timeout, out IntPtr result);
    [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int attribute, out Rect rect, int size);
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
        # PrintWindow includes invisible resize margins; capture the visible DWM frame only.
        $visible = New-Object InstallerUI+Rect
        if ([InstallerUI]::DwmGetWindowAttribute($window, 9, [ref]$visible, 16) -eq 0) {
            $crop = [System.Drawing.Rectangle]::new($visible.left-$rect.left, $visible.top-$rect.top, $visible.right-$visible.left, $visible.bottom-$visible.top)
            $capture = $bitmap.Clone($crop, $bitmap.PixelFormat)
            try { $capture.Save($path, [System.Drawing.Imaging.ImageFormat]::Png) } finally { $capture.Dispose() }
        } else { $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png) }
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
    $dpi = [InstallerUI]::GetDpiForWindow($window)
    $client = New-Object InstallerUI+Rect
    [InstallerUI]::GetClientRect($window, [ref]$client) | Out-Null
    Assert-UI ($client.right -eq [math]::Floor(835*$dpi/96) -and $client.bottom -eq [math]::Floor(605*$dpi/96)) 'Reference client dimensions'
    Assert-UI (([InstallerUI]::GetWindowLong($window,-16) -band 0x40000) -ne 0) 'Standard desktop caption frame'
    Assert-UI ([InstallerUI]::GetMenuState([InstallerUI]::GetSystemMenu($window,$false),0xF000,0) -eq [uint32]::MaxValue) 'Size must be absent from the system menu'
    $install = [InstallerUI]::GetDlgItem($window, 1)
    Assert-UI ((Count-Languages) -eq 2) 'Initial language count'
    Assert-UI ([InstallerUI]::Send($list,0x147,0,0).ToInt32() -eq 0) 'English must be selected'
    Assert-UI ([InstallerUI]::Text($window) -eq "Setup - Racall version $releaseLabel") 'English must be the default UI'
    Assert-UI ([InstallerUI]::IsWindowEnabled($install)) 'Install must initially be enabled'
    Assert-UI (!($controls | Where-Object { [InstallerUI]::Class($_) -in @('Edit','ListBox') })) 'No separate search or list'
    $texts = [InstallerUI]::Children($window) | ForEach-Object { [InstallerUI]::Text($_) }
    Assert-UI ($texts -contains 'Click Install to continue with the installation.') 'English continuation instruction'
    Capture-Window $window "$output/english.png"
    [InstallerUI]::Send($list,0x14F,1,0) | Out-Null
    Assert-UI ([InstallerUI]::Send($list,0x157,0,0).ToInt32() -eq 1) 'Dropdown must open'
    [InstallerUI]::Send($list,0x14F,0,0) | Out-Null
    [InstallerUI]::Select($list,1)
    Assert-UI ([InstallerUI]::Send($list,0x147,0,0).ToInt32() -eq 1) 'Russian must be selected'
    Assert-UI ([InstallerUI]::Text($window) -eq "Установка — Racall, версия $releaseLabel") 'Russian must apply immediately'
    Assert-UI ([InstallerUI]::Text($install) -match 'Установить') 'Translated install button'
    Assert-UI ([InstallerUI]::IsWindowEnabled($install)) 'Install remains enabled'
    $texts = [InstallerUI]::Children($window) | ForEach-Object { [InstallerUI]::Text($_) }
    Assert-UI ($texts -contains 'Нажмите «Установить», чтобы продолжить установку.') 'Russian continuation instruction'
    Capture-Window $window "$output/russian.png"
    [InstallerUI]::Select($list,0)
    Assert-UI ([InstallerUI]::Text($window) -eq "Setup - Racall version $releaseLabel") 'Switching back to English'
    [InstallerUI]::Select($list,1)
    $before = New-Object InstallerUI+Rect
    [InstallerUI]::GetWindowRect($window, [ref]$before) | Out-Null
    $point = (($before.bottom-2) -shl 16) -bor ($before.right-2)
    $result = [IntPtr]::Zero
    $handled = [InstallerUI]::SendMessageTimeout($window,0xA1,17,$point,2,500,[ref]$result)
    Assert-UI ($handled -ne [IntPtr]::Zero) 'Edge press must not enter an interactive resize loop'
    $after = New-Object InstallerUI+Rect
    [InstallerUI]::GetWindowRect($window, [ref]$after) | Out-Null
    Assert-UI ($before.right-$before.left -eq $after.right-$after.left -and $before.bottom-$before.top -eq $after.bottom-$after.top) 'Edge press must preserve window size'
    [InstallerUI]::Send($install,0xF5,0,0) | Out-Null
    Assert-UI ($fixture.WaitForExit(5000)) 'Helper must return after Install'
    Assert-UI ($fixture.ExitCode -eq 0) 'Successful selection exit code'
    $selection = Get-Content -LiteralPath $selectionFile -Raw
    Assert-UI ($selection -match 'language=1049') 'Selected Russian must reach parent'
    Assert-UI ($selection.Contains("directory=$chosenPath")) 'Chosen path with spaces must reach parent'
    Assert-UI (!(Test-Path -LiteralPath $chosenPath)) 'Helper must not install files'
    @{passed=$true; checks=@('Native frame geometry','Fixed window size','English default','Native dropdown opens','Immediate translation','No separate search or list','Language and path handoff'); fixture='Production language helper, test size 512 MiB'} |
        ConvertTo-Json | Set-Content -Encoding utf8 "$output/result.json"
    Get-Content "$output/result.json"
} finally {
    if (!$fixture.HasExited) { Stop-Process -Id $fixture.Id -Force }
}


# Exercise the same progress layout used by the real installer, without installing.
& $Compiler /WX /V2 "/DPROJECT_DIR=$repoRoot" "$repoRoot/installer/preview-progress.nsi"
if ($LASTEXITCODE) { throw 'Progress preview compilation failed.' }
$catalog = Get-Content "$repoRoot/installer/catalog.json" -Raw | ConvertFrom-Json
foreach ($entry in $catalog.languages) {
    $preview = Start-Process "$repoRoot/build/Racall-progress-preview.exe" -ArgumentList "/LANGUAGE=$($entry.windowsId)" -WindowStyle Hidden -PassThru
    try {
        $progress = $null
        for ($attempt=0; $attempt -lt 50; $attempt++) {
            $window = [InstallerUI]::Find($preview.Id)
            $controls = [InstallerUI]::Children($window)
            $progress = $controls | Where-Object { [InstallerUI]::GetDlgCtrlID($_) -eq 2004 } | Select-Object -First 1
            if ($progress -and [InstallerUI]::Send($progress,0x408,0,0).ToInt32() -eq 42) { break }
            Start-Sleep -Milliseconds 100
        }
        Assert-UI ($progress -and [InstallerUI]::Send($progress,0x408,0,0).ToInt32() -eq 42) 'Preview holds 42 percent'
        $page = [InstallerUI]::GetParent($progress)
        $nativeProgress = [InstallerUI]::GetDlgItem($page,1004)
        Assert-UI ($nativeProgress -ne [IntPtr]::Zero) 'Native engine progress handle retained'
        Assert-UI ([InstallerUI]::Text([InstallerUI]::GetDlgItem($page,2101)) -eq $entry.text.progressTitle) 'Localized progress heading'
        Assert-UI ([InstallerUI]::Text([InstallerUI]::GetDlgItem($page,2102)) -eq $entry.text.progressIntro) 'Localized progress introduction'
        $client = New-Object InstallerUI+Rect
        [InstallerUI]::GetClientRect($window,[ref]$client) | Out-Null
        $dpi = [InstallerUI]::GetDpiForWindow($window)
        Assert-UI ($client.right -eq [math]::Floor(835*$dpi/96) -and $client.bottom -eq [math]::Floor(605*$dpi/96)) 'Progress window matches welcome dimensions'
        $rect = New-Object InstallerUI+Rect
        [InstallerUI]::GetWindowRect($progress,[ref]$rect) | Out-Null
        Assert-UI ($rect.right-$rect.left -eq [math]::Floor(724*$dpi/96) -and $rect.bottom-$rect.top -eq [math]::Floor(28*$dpi/96)) 'Reference progress bar dimensions'
        $status = [InstallerUI]::GetDlgItem($page,1006)
        Assert-UI (([InstallerUI]::GetWindowLong($status,-16) -band 0x8080) -eq 0x8080) 'Paths are single-line and ampersands are literal'
        $cancel = [InstallerUI]::GetDlgItem($window,2)
        Assert-UI ([InstallerUI]::IsWindowEnabled($cancel)) 'Preview cancellation remains available'
        [InstallerUI]::ShowWindow($window,4) | Out-Null
        Start-Sleep -Milliseconds 800
        Capture-Window $window "$output/progress-preview-$($entry.windowsId).png"
        [InstallerUI]::Send($cancel,0xF5,0,0) | Out-Null
        Assert-UI ($preview.WaitForExit(3000)) 'Cancel closes progress preview'
    } finally { if (!$preview.HasExited) { Stop-Process -Id $preview.Id -Force } }
}
@{ passed=$true; checks=@('EN/RU progress text','Shared window dimensions','Native engine handles retained','Path ellipsis','Preview cancellation'); installationPerformed=$false } |
    ConvertTo-Json | Set-Content -Encoding utf8 "$output/progress-result.json"
Get-Content "$output/progress-result.json"

# A failed extraction must keep the second screen dismissible.
$preview = Start-Process "$repoRoot/build/Racall-progress-preview.exe" -ArgumentList '/FAILURE=1' -WindowStyle Hidden -PassThru
try {
 for ($attempt=0; $attempt -lt 50; $attempt++) {
  $window=[InstallerUI]::Find($preview.Id)
  $close=[InstallerUI]::GetDlgItem($window,2)
  if ([InstallerUI]::Text($close).Replace('&','') -eq 'Close') { break }
  Start-Sleep -Milliseconds 100
 }
 Assert-UI (([InstallerUI]::GetWindowLong($close,-16) -band 0x10000000) -ne 0) 'Failed progress page needs a visible Close button'
 Assert-UI ([InstallerUI]::IsWindowEnabled($close)) 'Failed progress page needs enabled Close button'
 [InstallerUI]::Send($close,0xF5,0,0) | Out-Null
 Assert-UI ($preview.WaitForExit(3000)) 'Failed preview closes without installing'
 'Simulated failure remains dismissible.'
} finally { if (!$preview.HasExited) { Stop-Process -Id $preview.Id -Force } }
