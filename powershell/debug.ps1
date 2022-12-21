Add-Type -AssemblyName System.Windows.Forms
Add-Type -Name ConsoleUtils -Namespace WPIA -MemberDefinition @'
   [DllImport("Kernel32.dll")]
   public static extern IntPtr GetConsoleWindow();
   [DllImport("user32.dll")]
   public static extern bool ShowWindow(IntPtr hWnd, Int32 nCmdShow);
'@

# Hide Powershell window
$hWnd = [WPIA.ConsoleUtils]::GetConsoleWindow()
[WPIA.ConsoleUtils]::ShowWindow($hWnd, 0)

Clear-Host

$WShell = New-Object -com "Wscript.Shell"

$index = 0
while ($true)
{
  # Press ScrollLock key
  $WShell.sendkeys("{NUMLOCK}")
  Start-Sleep -Milliseconds 200
  $WShell.sendkeys("{NUMLOCK}")
  
  # Sleep
  Start-Sleep -Seconds 10
}
