"""가상 게임패드 출력 (Windows, ViGEmBus + vgamepad).

매크로가 '게임패드 버튼'을 눌러주려면 가상 Xbox360 컨트롤러를 만들어 그 버튼을
눌러야 한다. vgamepad 라이브러리(내부적으로 ViGEmClient.dll)를 사용하며,
실제 동작에는 사용자 PC에 ViGEmBus 드라이버가 설치돼 있어야 한다.

vgamepad 가 없거나 드라이버 미설치/비-Windows 면 available=False 가 되고,
press/release/tap 은 조용히 False 를 돌려준다(앱은 안내 문구만 표시).

이름 규약은 gamepad_input 과 동일한 'Gamepad.XXX' 를 받는다.
"""

import sys
import threading
import time

_IS_WIN = sys.platform == 'win32'

try:
    import vgamepad as _vg
except Exception:
    _vg = None

_PREFIX = 'Gamepad.'

_BUTTON_MAP = {}
if _vg is not None:
    _B = _vg.XUSB_BUTTON
    _BUTTON_MAP = {
        'A': _B.XUSB_GAMEPAD_A,
        'B': _B.XUSB_GAMEPAD_B,
        'X': _B.XUSB_GAMEPAD_X,
        'Y': _B.XUSB_GAMEPAD_Y,
        'LB': _B.XUSB_GAMEPAD_LEFT_SHOULDER,
        'RB': _B.XUSB_GAMEPAD_RIGHT_SHOULDER,
        'Back': _B.XUSB_GAMEPAD_BACK,
        'Start': _B.XUSB_GAMEPAD_START,
        'LStick': _B.XUSB_GAMEPAD_LEFT_THUMB,
        'RStick': _B.XUSB_GAMEPAD_RIGHT_THUMB,
        'DPadUp': _B.XUSB_GAMEPAD_DPAD_UP,
        'DPadDown': _B.XUSB_GAMEPAD_DPAD_DOWN,
        'DPadLeft': _B.XUSB_GAMEPAD_DPAD_LEFT,
        'DPadRight': _B.XUSB_GAMEPAD_DPAD_RIGHT,
        'Guide': _B.XUSB_GAMEPAD_GUIDE,
    }

_STICK_MAX = 32767


def is_gamepad_output(name):
    return bool(name) and str(name).startswith(_PREFIX)


class VirtualPad:
    """가상 Xbox360 패드. 첫 출력 시점에 지연 생성한다."""

    def __init__(self):
        self._gp = None
        self._lock = threading.Lock()
        self._active = set()
        self.last_error = None
        self.supported = _vg is not None and _IS_WIN

    def _ensure(self):
        if self._gp is not None:
            return True
        if not self.supported:
            return False
        try:
            self._gp = _vg.VX360Gamepad()
            return True
        except Exception as exc:
            self.last_error = exc
            self._gp = None
            return False

    def _apply_locked(self):
        gp = self._gp
        gp.reset()
        lx = ly = rx = ry = 0
        for name in self._active:
            short = name[len(_PREFIX):] if name.startswith(_PREFIX) else name
            btn = _BUTTON_MAP.get(short)
            if btn is not None:
                gp.press_button(button=btn)
            elif short == 'LT':
                gp.left_trigger(value=255)
            elif short == 'RT':
                gp.right_trigger(value=255)
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
        gp.left_joystick(x_value=lx, y_value=ly)
        gp.right_joystick(x_value=rx, y_value=ry)
        gp.update()

    def press(self, name):
        with self._lock:
            if not self._ensure():
                return False
            self._active.add(name)
            try:
                self._apply_locked()
                return True
            except Exception as exc:
                self.last_error = exc
                return False

    def release(self, name):
        with self._lock:
            if self._gp is None:
                return False
            self._active.discard(name)
            try:
                self._apply_locked()
                return True
            except Exception as exc:
                self.last_error = exc
                return False

    def tap(self, name, hold=0.04):
        if not self.press(name):
            return False
        time.sleep(hold)
        return self.release(name)

    def release_all(self):
        with self._lock:
            if self._gp is None:
                return
            self._active.clear()
            try:
                self._apply_locked()
            except Exception:
                pass
