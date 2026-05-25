"""게임용 저수준 입력 전송 (Windows SendInput, 스캔코드 기반).

대부분의 게임(DirectInput/RawInput)은 pynput 이 기본으로 보내는 가상키코드(VK)
입력을 무시하고 물리 스캔코드만 인식한다. 그래서 키보드는 KEYEVENTF_SCANCODE 로,
마우스는 SendInput 으로 보낸다. 실패하거나 비-Windows 환경이면 pynput 으로 폴백한다.

pynput 의 Controller 와 동일한 press()/release() 인터페이스를 제공하므로
기존 호출부를 그대로 둔 채 컨트롤러만 교체하면 된다.
"""

import sys

_IS_WIN = sys.platform == 'win32'

if _IS_WIN:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL('user32', use_last_error=True)
    ULONG_PTR = wintypes.WPARAM  # 32비트=c_ulong, 64비트=c_ulonglong

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    _user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)
    _user32.SendInput.restype = wintypes.UINT
    _user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
    _user32.MapVirtualKeyW.restype = wintypes.UINT
    _user32.VkKeyScanW.argtypes = (wintypes.WCHAR,)
    _user32.VkKeyScanW.restype = wintypes.SHORT

    _INPUT_MOUSE = 0
    _INPUT_KEYBOARD = 1
    _KEYEVENTF_EXTENDEDKEY = 0x0001
    _KEYEVENTF_KEYUP = 0x0002
    _KEYEVENTF_SCANCODE = 0x0008
    _MAPVK_VK_TO_VSC = 0

    _MOUSEEVENTF = {
        ('left', True): (0x0002, 0),
        ('left', False): (0x0004, 0),
        ('right', True): (0x0008, 0),
        ('right', False): (0x0010, 0),
        ('middle', True): (0x0020, 0),
        ('middle', False): (0x0040, 0),
        ('x1', True): (0x0080, 0x0001),
        ('x1', False): (0x0100, 0x0001),
        ('x2', True): (0x0080, 0x0002),
        ('x2', False): (0x0100, 0x0002),
    }

    # 확장키(0xE0 접두) — 화살표/Home/End/Ins/Del/우Ctrl/우Alt/Numpad÷/NumLock/Win 등
    _EXTENDED_VKS = frozenset({
        0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
        0x2D, 0x2E, 0x6F, 0x90, 0xA3, 0xA5, 0x5B, 0x5C, 0x5D,
    })

    def _vk_of(kobj):
        val = getattr(kobj, 'value', None)
        if val is not None:
            vk = getattr(val, 'vk', None)
            if vk is not None:
                return vk
        vk = getattr(kobj, 'vk', None)
        if vk is not None:
            return vk
        ch = getattr(kobj, 'char', None)
        if ch:
            res = _user32.VkKeyScanW(ch)
            if res != -1:
                return res & 0xFF
        return None

    def _send_key(vk, keyup):
        scan = _user32.MapVirtualKeyW(vk, _MAPVK_VK_TO_VSC)
        if scan:
            wvk, wscan = 0, scan
            flags = _KEYEVENTF_SCANCODE
            if vk in _EXTENDED_VKS:
                flags |= _KEYEVENTF_EXTENDEDKEY
        else:
            wvk, wscan = vk, 0  # 스캔코드 매핑 없는 미디어키 등은 VK 로
            flags = 0
        if keyup:
            flags |= _KEYEVENTF_KEYUP
        inp = _INPUT(type=_INPUT_KEYBOARD)
        inp.u.ki = _KEYBDINPUT(wvk, wscan, flags, 0, 0)
        return _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))

    def _send_mouse(name, down):
        key = _MOUSEEVENTF.get((name, down))
        if key is None:
            return 0
        flags, data = key
        inp = _INPUT(type=_INPUT_MOUSE)
        inp.u.mi = _MOUSEINPUT(0, 0, data, flags, 0, 0)
        return _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


class GameKeyboard:
    """pynput keyboard.Controller 호환 래퍼 — 스캔코드 SendInput, 실패시 폴백."""

    def __init__(self, fallback):
        self._fallback = fallback

    def press(self, kobj):
        if _IS_WIN:
            vk = _vk_of(kobj)
            if vk is not None and _send_key(vk, False):
                return
        self._fallback.press(kobj)

    def release(self, kobj):
        if _IS_WIN:
            vk = _vk_of(kobj)
            if vk is not None and _send_key(vk, True):
                return
        self._fallback.release(kobj)


class GameMouse:
    """pynput mouse.Controller 호환 래퍼 (press/release만 게임용으로 보냄)."""

    def __init__(self, fallback):
        self._fallback = fallback

    def __getattr__(self, name):
        # position 등 나머지 속성은 원래 컨트롤러로 위임
        return getattr(self._fallback, name)

    def press(self, bobj):
        if _IS_WIN:
            name = getattr(bobj, 'name', '')
            if name and _send_mouse(name, True):
                return
        self._fallback.press(bobj)

    def release(self, bobj):
        if _IS_WIN:
            name = getattr(bobj, 'name', '')
            if name and _send_mouse(name, False):
                return
        self._fallback.release(bobj)
