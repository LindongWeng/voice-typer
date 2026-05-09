import pyperclip
import subprocess
import time


def inject_text(text: str) -> bool:
    """
    将文字写入剪贴板，尝试模拟 Cmd+V 粘贴。
    返回 True 表示粘贴成功，False 表示无活动光标（需手动粘贴）。
    """
    pyperclip.copy(text)
    time.sleep(0.1)
    result = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to keystroke "v" using command down'],
        capture_output=True, text=True
    )
    return result.returncode == 0
