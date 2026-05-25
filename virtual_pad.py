"""가상 게임패드 출력 (Windows, ViGEmBus + 번들된 ViGEmClient.dll).

vgamepad 라이브러리(설치 시 드라이버 MSI 를 실행해 CI/빌드를 멈추게 함) 대신,
ViGEmClient.dll 을 저장소에 동봉하고 ctypes 로 직접 호출한다. pip 설치가 전혀
필요 없으므로 빌드가 안정적이다.

실제 가상 컨트롤러 생성에는 사용자 PC 에 ViGEmBus 드라이버가 설치돼 있어야 한다
(없으면 connect 단계에서 BUS_NOT_FOUND 가 나고 supported=True 지만 press 는 False).

이름 규약은 gamepad_input 과 동일한 'Gamepad.XXX' 를 받는다.
"""

import os
import sys
import threading
import time

_IS_WIN = sys.platform == 'win32'
_PREFIX = 'Gamepad.'

_VIGEM_ERROR_NONE = 0x20000000

# XUSB_BUTTON 비트 (XInput wButtons 와 동일)
_BUTTON_MAP = {
    'DPadUp': 0x0001, 'DPadDown': 0x0002, 'DPadLeft': 0x0004, 'DPadRight': 0x0008,
    'Start': 0x0010, 'Back': 0x0020, 'LStick': 0x0040, 'RStick': 0x0080,
    'LB': 0x0100, 'RB': 0x0200, 'Guide': 0x0400,
    'A': 0x1000, 'B': 0x2000, 'X': 0x4000, 'Y': 0x8000,
}
_STICK_MAX = 32767

_dll = None
_XUSB_REPORT = None

if _IS_WIN:
    import ctypes

    class _XUSB_REPORT_STRUCT(ctypes.Structure):
        _fields_ = [
            ('wButtons', ctypes.c_ushort),
            ('bLeftTrigger', ctypes.c_ubyte),
            ('bRightTrigger', ctypes.c_ubyte),
            ('sThumbLX', ctypes.c_short),
            ('sThumbLY', ctypes.c_short),
            ('sThumbRX', ctypes.c_short),
            ('sThumbRY', ctypes.c_short),
        ]

    _XUSB_REPORT = _XUSB_REPORT_STRUCT

    def _find_dll():
        names = ('ViGEmClient.dll',)
        bases = []
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            bases.append(os.path.join(meipass, 'vigem'))
            bases.append(meipass)
        here = os.path.dirname(os.path.abspath(__file__))
        bases.append(os.path.join(here, 'vigem'))
        bases.append(here)
        for base in bases:
            for n in names:
                p = os.path.join(base, n)
                if os.path.exists(p):
                    return p
        return None

    try:
        _dll_path = _find_dll()
        if _dll_path:
            _dll = ctypes.WinDLL(_dll_path)
            _dll.vigem_alloc.restype = ctypes.c_void_p
            _dll.vigem_alloc.argtypes = []
            _dll.vigem_connect.restype = ctypes.c_int
            _dll.vigem_connect.argtypes = [ctypes.c_void_p]
            _dll.vigem_disconnect.argtypes = [ctypes.c_void_p]
            _dll.vigem_free.argtypes = [ctypes.c_void_p]
            _dll.vigem_target_x360_alloc.restype = ctypes.c_void_p
            _dll.vigem_target_x360_alloc.argtypes = []
            _dll.vigem_target_free.argtypes = [ctypes.c_void_p]
            _dll.vigem_target_add.restype = ctypes.c_int
            _dll.vigem_target_add.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            _dll.vigem_target_remove.restype = ctypes.c_int
            _dll.vigem_target_remove.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            _dll.vigem_target_x360_update.restype = ctypes.c_int
            _dll.vigem_target_x360_update.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, _XUSB_REPORT_STRUCT]
    except Exception:
        _dll = None


def is_gamepad_output(name):
    return bool(name) and str(name).startswith(_PREFIX)


class VirtualPad:
    """ViGEmClient.dll 로 가상 Xbox360 패드를 만든다. 첫 출력 시 지연 연결."""

    def __init__(self):
        self._client = None
        self._target = None
        self._lock = threading.Lock()
        self._active = set()
        self.last_error = None
        self.supported = _IS_WIN and _dll is not None

    def _ensure(self):
        if self._target is not None:
            return True
        if not self.supported:
            self.last_error = 'ViGEmClient.dll 없음'
            return False
        try:
            self._client = _dll.vigem_alloc()
            if not self._client:
                self.last_error = 'vigem_alloc 실패'
                return False
            r = _dll.vigem_connect(self._client)
            if r != _VIGEM_ERROR_NONE:
                self.last_error = 'vigem_connect 0x%08X (드라이버 미설치?)' % (r & 0xFFFFFFFF)
                return False
            self._target = _dll.vigem_target_x360_alloc()
            if not self._target:
                self.last_error = 'x360_alloc 실패'
                return False
            r = _dll.vigem_target_add(self._client, self._target)
            if r != _VIGEM_ERROR_NONE:
                self.last_error = 'target_add 0x%08X' % (r & 0xFFFFFFFF)
                self._target = None
                return False
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def _apply_locked(self):
        buttons = 0
        lt = rt = 0
        lx = ly = rx = ry = 0
        for name in self._active:
            short = name[len(_PREFIX):] if name.startswith(_PREFIX) else name
            bit = _BUTTON_MAP.get(short)
            if bit is not None:
                buttons |= bit
            elif short == 'LT':
                lt = 255
            elif short == 'RT':
                rt = 255
            elif short == 'LStickLeft':
                lx = -_STICK_MAX
            elif short == 'LStickRight':
                lx = _STICK_MAX
            elif short == 'LStickUp':
                ly = _STICK_MAX
            elif short == 'LStickDown':
                ly = -_STICK_MAX
            elif short == 'RStickLeft':
                rx = -_STICK_MAX
            elif short == 'RStickRight':
                rx = _STICK_MAX
            elif short == 'RStickUp':
                ry = _STICK_MAX
            elif short == 'RStickDown':
                ry = -_STICK_MAX
        report = _XUSB_REPORT(buttons, lt, rt, lx, ly, rx, ry)
        r = _dll.vigem_target_x360_update(self._client, self._target, report)
        return r == _VIGEM_ERROR_NONE

    def press(self, name):
        with self._lock:
            if not self._ensure():
                return False
            self._active.add(name)
            try:
                return self._apply_locked()
            except Exception as exc:
                self.last_error = str(exc)
                return False

    def release(self, name):
        with self._lock:
            if self._target is None:
                return False
            self._active.discard(name)
            try:
                return self._apply_locked()
            except Exception as exc:
                self.last_error = str(exc)
                return False

    def tap(self, name, hold=0.04):
        if not self.press(name):
            return False
        time.sleep(hold)
        return self.release(name)

    def is_active(self, name):
        return name in self._active

    def release_all(self):
        with self._lock:
            if self._target is None:
                return
            self._active.clear()
            try:
                self._apply_locked()
            except Exception:
                pass
