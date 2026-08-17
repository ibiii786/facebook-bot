import sys
import json
import subprocess
import tempfile
import os


def pick_with_powershell(dialog_type="files"):
    """Use PowerShell's System.Windows.Forms dialogs which always appear on top."""
    try:
        if dialog_type == "files":
            ps_script = r"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = "Select Image Files"
$dialog.Multiselect = $true
$dialog.Filter = "Image Files (*.png;*.jpg;*.jpeg;*.webp;*.gif;*.bmp)|*.png;*.jpg;*.jpeg;*.webp;*.gif;*.bmp|All Files (*.*)|*.*"
$form = New-Object System.Windows.Forms.Form
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.WindowState = 'Minimized'
$form.Show()
$result = $dialog.ShowDialog($form)
$form.Close()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    $dialog.FileNames | ConvertTo-Json -Compress
} else {
    "[]"
}
"""
        elif dialog_type == "video":
            ps_script = r"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = "Select Video File"
$dialog.Multiselect = $false
$dialog.Filter = "Video Files (*.mp4;*.mov;*.avi;*.mkv;*.webm)|*.mp4;*.mov;*.avi;*.mkv;*.webm|All Files (*.*)|*.*"
$form = New-Object System.Windows.Forms.Form
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.WindowState = 'Minimized'
$form.Show()
$result = $dialog.ShowDialog($form)
$form.Close()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    '["' + $dialog.FileName.Replace('\', '\\') + '"]'
} else {
    "[]"
}
"""
        elif dialog_type == "folder":
            ps_script = r"""
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "Select Directory / Folder"
$dialog.ShowNewFolderButton = $false
$form = New-Object System.Windows.Forms.Form
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.WindowState = 'Minimized'
$form.Show()
$result = $dialog.ShowDialog($form)
$form.Close()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    '["' + $dialog.SelectedPath.Replace('\', '\\') + '"]'
} else {
    "[]"
}
"""
        else:
            return []

        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=300
        )

        output = result.stdout.strip()
        if not output:
            return []

        # PowerShell may return a single string instead of array for one item
        parsed = json.loads(output)
        if isinstance(parsed, str):
            return [parsed] if parsed else []
        return parsed if isinstance(parsed, list) else []

    except Exception as e:
        sys.stderr.write(f"PowerShell file picker error: {e}\n")
        return []


if __name__ == "__main__":
    dtype = sys.argv[1] if len(sys.argv) > 1 else "files"
    paths = pick_with_powershell(dtype)
    print("PICKER_OUTPUT:" + json.dumps(paths))
