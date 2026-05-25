import ctypes
import json
import os
import sys
import threading
import time
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont
from pynput import keyboard, mouse

try:
    import gamepad_input
    GAMEPAD_SUPPORTED = bool(getattr(gamepad_input, 'AVAILABLE', False))
except Exception:
    gamepad_input = None
    GAMEPAD_SUPPORTED = False

try:
    import win_input
except Exception:
    win_input = None

try:
    import virtual_pad
except Exception:
    virtual_pad = None


class GamepadButton:
    """게임패드 버튼을 키보드/마우스와 동일한 핫키 체계로 흘려보내기 위한 합성 키 객체."""

    def __init__(self, name = None):
        self.gamepad_name = name
NUMPAD_VK_TO_NAME = {
    96: 'Numpad0',
    97: 'Numpad1',
    98: 'Numpad2',
    99: 'Numpad3',
    100: 'Numpad4',
    101: 'Numpad5',
    102: 'Numpad6',
    103: 'Numpad7',
    104: 'Numpad8',
    105: 'Numpad9',
    106: 'Numpad*',
    107: 'Numpad+',
    109: 'Numpad-',
    110: 'Numpad.',
    111: 'Numpad/' }
NUMPAD_NAME_TO_VK = {v: k for k, v in NUMPAD_VK_TO_NAME.items()}

def key_to_str(k = None):
    if isinstance(k, GamepadButton):
        return k.gamepad_name or ''
    if isinstance(k, keyboard.Key):
        return f'''Key.{k.name}'''
    if isinstance(k, keyboard.KeyCode):
        vk = getattr(k, 'vk', None)
        if vk in NUMPAD_VK_TO_NAME:
            return f'''VK.{vk}:{NUMPAD_VK_TO_NAME[vk]}'''
        ch = k.char
        if ch is not None and ch != '':
            return ch
        if vk is not None:
            return f'''VK.{vk}'''
    return ''


def str_to_key(s = None):
    if not s:
        return None
    if s.startswith('Gamepad.'):
        return None
    if len(s) == 1:
        return keyboard.KeyCode.from_char(s)
    if s.startswith('Key.'):
        name = s.split('.', 1)[1]
        try:
            return getattr(keyboard.Key, name)
        except Exception:
            return None
    if s.startswith('VK.'):
        body = s[3:]
        vk_str = body.split(':', 1)[0]
        try:
            vk = int(vk_str)
            return keyboard.KeyCode.from_vk(vk)
        except Exception:
            return None
    return None

MOUSE_BUTTON_LABELS = {
    'left': '왼쪽버튼',
    'right': '오른쪽버튼',
    'middle': '휠클릭' }
BASIC_MOUSE_BUTTON_NAMES = set(MOUSE_BUTTON_LABELS.keys())
CUSTOM_MOUSE_PREFIX = 'MouseCustom.'
BASIC_MOUSE_PREFIX = 'Mouse.'

def mouse_button_text_from_obj(button = None):
    
    try:
        button_name = getattr(button, 'name', '')
        if button_name:
            return f'''Button.{button_name}'''
    except Exception:
        pass

    
    try:
        return str(button)
    except Exception:
        return 'Unknown'



def mouse_button_name_from_obj(button = None):
    if button == mouse.Button.left:
        return 'left'
    if button == mouse.Button.right:
        return 'right'
    if button == mouse.Button.middle:
        return 'middle'
    return ''


def mouse_button_storage_from_obj(button = None):
    basic_name = mouse_button_name_from_obj(button)
    if basic_name:
        return ('basic', basic_name)
    button_text = mouse_button_text_from_obj(button)
    if button_text and button_text != 'Unknown':
        return ('custom', button_text)
    return ('', '')


def mouse_button_obj_from_storage(button_type = None, button = None):
    button_type = button_type if button_type in frozenset({'basic', 'custom'}) else 'basic'
    button = str(button or '')
    if button_type == 'basic':
        if button == 'left':
            return mouse.Button.left
        if button == 'right':
            return mouse.Button.right
        if button == 'middle':
            return mouse.Button.middle
        return None
    if button.startswith('Button.'):
        name = button.split('.', 1)[1]
        
        try:
            return getattr(mouse.Button, name)
        except Exception:
            return None

        return None


def mouse_button_obj_from_name(name = None):
    if name in BASIC_MOUSE_BUTTON_NAMES:
        return mouse_button_obj_from_storage('basic', name)
    if isinstance(name, str) and name.startswith('Button.'):
        return mouse_button_obj_from_storage('custom', name)


def mouse_button_label(name = None):
    return MOUSE_BUTTON_LABELS.get(name, '')


def mouse_button_display_text(button_type = None, button = None):
    button_type = button_type if button_type in frozenset({'basic', 'custom'}) else 'basic'
    button = str(button or '')
    if button_type == 'basic':
        label = mouse_button_label(button)
        if label:
            return label
        return button
    return button


def mouse_button_hotkey(name = None, button_type = None):
    button_type = button_type if button_type in frozenset({'basic', 'custom'}) else 'basic'
    name = str(name or '')
    if button_type == 'basic' and name in BASIC_MOUSE_BUTTON_NAMES:
        return f'''Mouse.{name}'''
    if button_type == 'custom' and name:
        return f'''{CUSTOM_MOUSE_PREFIX}{name}'''
    return ''


def mouse_hotkey_storage(value = None):
    if not isinstance(value, str):
        return ('', '')
    if value.startswith(CUSTOM_MOUSE_PREFIX):
        button = value[len(CUSTOM_MOUSE_PREFIX):]
        if button:
            return ('custom', button)
        return ('', '')
    if value.startswith(BASIC_MOUSE_PREFIX):
        name = value.split('.', 1)[1]
        if name in BASIC_MOUSE_BUTTON_NAMES:
            return ('basic', name)
    return ('', '')


def mouse_hotkey_name(value = None):
    (button_type, button) = mouse_hotkey_storage(value)
    if button_type == 'basic':
        return button
    return ''


def is_mouse_hotkey(value = None):
    (button_type, button) = mouse_hotkey_storage(value)
    return bool(button_type and button)


def mouse_hotkey_from_obj(button = None):
    (button_type, button_value) = mouse_button_storage_from_obj(button)
    if button_type and button_value:
        return mouse_button_hotkey(button_value, button_type)
    return ''


def normalize_mouse_button_type(button_type = None, button = None):
    if button_type in frozenset({'basic', 'custom'}):
        return button_type
    if button in BASIC_MOUSE_BUTTON_NAMES:
        return 'basic'
    if isinstance(button, str) and button.startswith('Button.'):
        return 'custom'
    return 'basic'


def is_basic_mouse_button_obj(button = None):
    return mouse_button_name_from_obj(button) in BASIC_MOUSE_BUTTON_NAMES


def hotkey_display_text(value = None):
    if value and str(value).startswith('Gamepad.'):
        if gamepad_input is not None:
            return gamepad_input.display_text(value)
        return value
    (button_type, button) = mouse_hotkey_storage(value)
    if button_type and button:
        return f'''Mouse.{mouse_button_display_text(button_type, button)}'''
    return value


def normalize_program_process_name(value = None):
    value = os.path.basename(str(value or '').strip())
    return value


def _windows_process_name_from_pid(pid = None):
    if not sys.platform.startswith('win') or not pid:
        return ''
    try:
        kernel32 = ctypes.windll.kernel32
        process_query_limited_information = 4096
        kernel32.OpenProcess.argtypes = [
            ctypes.c_uint32,
            ctypes.c_bool,
            ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.QueryFullProcessImageNameW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_wchar_p,
            ctypes.POINTER(ctypes.c_uint32)]
        kernel32.QueryFullProcessImageNameW.restype = ctypes.c_bool
        kernel32.CloseHandle.argtypes = [
            ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_bool
        handle = kernel32.OpenProcess(process_query_limited_information, False, int(pid))
        if not handle:
            return ''
    except Exception:
        return ''
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = ctypes.c_uint32(len(buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return normalize_program_process_name(buffer.value)
        return ''
    finally:
        kernel32.CloseHandle(handle)



def _windows_window_title(hwnd = None):
    if not sys.platform.startswith('win') or not hwnd:
        return ''

    try:
        user32 = ctypes.windll.user32
        user32.GetWindowTextLengthW.argtypes = [
            ctypes.c_void_p]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        length = int(user32.GetWindowTextLengthW(hwnd))
        if length <= 0:
            return ''
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if not buffer.value:
            return ''
        return str(buffer.value).strip()
    except Exception:
        return ''



def get_foreground_process_name():
    if not sys.platform.startswith('win'):
        return ''
    
    try:
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.argtypes = []
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetWindowThreadProcessId.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32)]
        user32.GetWindowThreadProcessId.restype = ctypes.c_uint32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ''
        pid = ctypes.c_uint32(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return _windows_process_name_from_pid(int(pid.value))
    except Exception:
        return ''



def is_diablo_program_item(item = None):
    if not isinstance(item, dict):
        return False
    process_name = str(item.get('process', '') or '').lower()
    title = str(item.get('title', '') or '').lower()
    display = str(item.get('display', '') or '').lower()
    combined_text = f'''{process_name} {title} {display}'''
    return 'diablo' in combined_text or '디아블로' in combined_text


def active_program_sort_key(item = None):
    process_name = str(item.get('process', '') or '').lower()
    title = str(item.get('title', '') or '').lower()
    if is_diablo_program_item(item):
        return (0, process_name, title)
    return (1, process_name, title)


def enumerate_running_window_programs():
    if not sys.platform.startswith('win'):
        return []
    programs_by_name = { }
    
    try:
        user32 = ctypes.windll.user32
        enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows.argtypes = [
            enum_windows_proc,
            ctypes.c_void_p]
        user32.EnumWindows.restype = ctypes.c_bool
        user32.IsWindowVisible.argtypes = [
            ctypes.c_void_p]
        user32.IsWindowVisible.restype = ctypes.c_bool
        user32.GetWindowThreadProcessId.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32)]
        user32.GetWindowThreadProcessId.restype = ctypes.c_uint32
        
        def callback(hwnd = None, lparam = None):
            
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                title = _windows_window_title(hwnd)
                if not title:
                    return True
                pid = ctypes.c_uint32(0)
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                process_name = _windows_process_name_from_pid(int(pid.value))
                if not process_name:
                    return True
                key = process_name.lower()
                if key not in programs_by_name:
                    programs_by_name[key] = {
                        'process': process_name,
                        'title': title,
                        'display': f'''{process_name} - {title}''' }
                return True
            except Exception:
                return True


        enum_proc = enum_windows_proc(callback)
        user32.EnumWindows(enum_proc, None)
    except Exception:
        return []
    return sorted(programs_by_name.values(), key = active_program_sort_key)


def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    # onefile(.exe)로 묶인 읽기 전용 리소스는 _MEIPASS 임시폴더에 풀린다.
    base = getattr(sys, '_MEIPASS', None)
    if base:
        bundled = os.path.join(base, name)
        if os.path.exists(bundled):
            return bundled
    return os.path.join(get_app_dir(), name)


def get_last_settings_path():
    return os.path.join(get_app_dir(), 'last_settings.json')


def parse_interval(text = None):
    v = float(text)
    v = round(v, 4)
    if v < 0.0001:
        v = 0.0001
    return v


def format_interval_value(value = None):
    
    try:
        v = float(value)
    except Exception:
        v = 0.0001

    v = round(v, 4)
    text = f'''{v:.4f}'''.rstrip('0').rstrip('.')
    if text:
        return text
    return '0.0001'


class MacroApp(tk.Tk):
    
    def __init__(self = None):
        super().__init__()
        self.title('매크로 (게임패드 지원판 v6)')
        self._set_window_icon()
        self.resizable(True, True)
        self.start_keys = [
            'Key.f1']
        self.stop_keys = [
            'Key.f2']
        self.pause_key_items = [
            {
                'key': '`',
                'mode': 'hold' }]
        self.pause_hold_keys = self._pause_key_values()
        self.start_key_str = self.start_keys[0]
        self.stop_key_str = self.stop_keys[0]
        self.loot_hold_key_str = 'Key.f3'
        self.quick_right_hold_key_str = 'Key.f4'
        self.start_stop_same_key = False
        self._stop_keys_before_same_toggle = list(self.stop_keys)
        self.actions = []
        self.trigger_actions = []
        self.running = False
        self.triggers_enabled = False
        self.paused_hold = False
        self.loot_hold_active = False
        self.quick_click_active = False
        self.quick_click_button = ''
        self.center_status_enabled = False
        self.center_status_targets = [
            'monitor:0']
        self.center_status_shape = 'circle'
        self.center_status_show_text = False
        self.center_status_size_percent = 100
        self.center_status_overlays = { }
        self.center_status_transparent_color = '#010203'
        self.active_program_all = True
        self.active_program_targets = []
        self._active_program_blocked = False
        self._status_refresh_after_id = None
        self._center_overlay_reposition_after_id = None
        self._center_overlay_click_through_retry_after_id = None
        self._last_status_indicator_mode = None
        self._last_center_status_enabled = None
        self._last_center_status_targets_key = None
        self._last_center_status_rects_key = None
        self._last_center_status_shape = None
        self._last_center_status_show_text = None
        self._last_center_status_size_percent = None
        self._worker_threads = []
        self._held_keys = []
        self._held_mouse = []
        self._held_pad = []
        self.virtual_pad = virtual_pad.VirtualPad() if virtual_pad is not None else None
        self._run_lock = threading.Lock()
        self._input_block_lock = threading.Lock()
        self._input_block_count = 0
        self._pressed_pause_inputs = set()
        self._toggle_pause_active_key = ''
        self._trigger_lock = threading.Lock()
        self._pressed_trigger_keys = set()
        self._pressed_trigger_mouse_inputs = set()
        self._suppress_trigger_until = 0
        self._trigger_epoch = 0
        self._triggers_enabled_before_pause = False
        self._loot_triggers_enabled_before = False
        self._loot_click_thread = None
        self._loot_click_interval = 0.025
        self._active_trigger_ids = set()
        self._trigger_run_versions = { }
        self._suppressed_trigger_inputs = { }
        self.kb_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()
        if win_input is not None:
            self.kb_controller = win_input.GameKeyboard(self.kb_controller)
            self.mouse_controller = win_input.GameMouse(self.mouse_controller)
        self._last_settings_path = get_last_settings_path()
        self._load_last_settings_silent()
        self._build_ui()
        self._fit_window_to_content()
        self.bind('<Configure>', self._on_main_window_configure, add = '+')
        self._start_global_listener()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    
    def _set_window_icon(self):
        icon_path = resource_path('dia_logo.png')
        if not os.path.exists(icon_path):
            return None
        
        try:
            self._app_icon = tk.PhotoImage(file = icon_path)
            self.iconphoto(True, self._app_icon)
            return None
        except Exception:
            return None


    
    def _create_vertical_scroll_area(self, parent):
        outer = ttk.Frame(parent)
        outer.pack(fill = 'both', expand = True)
        canvas = tk.Canvas(outer, highlightthickness = 0, borderwidth = 0)
        scrollbar = ttk.Scrollbar(outer, orient = 'vertical')
        content = ttk.Frame(canvas)
        
        try:
            canvas.configure(background = parent.cget('background'))
        except Exception:
            pass

        window_id = canvas.create_window((0, 0), window = content, anchor = 'nw')
        canvas.pack(side = 'left', fill = 'both', expand = True)
        scrollbar.pack(side = 'right', fill = 'y')
        scrollbar.configure(command = canvas.yview)
        
        def update_scrollbar(first = None, last = None):

            try:
                content_height = content.winfo_reqheight()
                canvas_height = canvas.winfo_height()
                if content_height <= canvas_height:
                    scrollbar.set(0, 1)
                    try:
                        scrollbar.state([
                            'disabled'])
                    except Exception:
                        pass
                    return None
                scrollbar.set(first, last)
                try:
                    scrollbar.state([
                        '!disabled'])
                except Exception:
                    pass
                return None
            except Exception:
                try:
                    scrollbar.set(first, last)
                except Exception:
                    pass
                return None


        canvas.configure(yscrollcommand = update_scrollbar)
        
        def refresh_scroll_region():
            
            try:
                canvas.configure(scrollregion = canvas.bbox('all'))
                content_height = content.winfo_reqheight()
                canvas_height = canvas.winfo_height()
                if content_height <= canvas_height:
                    canvas.yview_moveto(0)
                    scrollbar.set(0, 1)
                    try:
                        scrollbar.state([
                            'disabled'])
                    except Exception:
                        pass
                    return None
                try:
                    scrollbar.state([
                        '!disabled'])
                except Exception:
                    pass
                return None
            except Exception:
                return None


        
        def on_canvas_configure(event = None):
            
            try:
                canvas.itemconfigure(window_id, width = event.width)
            except Exception:
                pass

            refresh_scroll_region()

        
        def is_inner_scroll_widget(widget):
            
            try:
                return isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox))
            except Exception:
                return False


        
        def on_mousewheel(event = None):
            
            try:
                if content.winfo_reqheight() <= canvas.winfo_height():
                    return None
                event_widget = getattr(event, 'widget', None)
                if event_widget is not None and is_inner_scroll_widget(event_widget):
                    return None
                if getattr(event, 'num', None) == 4:
                    move = -1
                elif getattr(event, 'num', None) == 5:
                    move = 1
                else:
                    delta = getattr(event, 'delta', 0)
                    move = -1 * int(delta / 120)
                    if move == 0:
                        move = -1 if delta > 0 else 1
                canvas.yview_scroll(move, 'units')
                return 'break'
            except Exception:
                return None


        
        def bind_mousewheel_to_widget(widget = None):
            
            try:
                if is_inner_scroll_widget(widget):
                    return None
                if not getattr(widget, '_macro_scroll_wheel_bound', False):
                    widget.bind('<MouseWheel>', on_mousewheel, add = '+')
                    widget.bind('<Button-4>', on_mousewheel, add = '+')
                    widget.bind('<Button-5>', on_mousewheel, add = '+')
                    setattr(widget, '_macro_scroll_wheel_bound', True)
                for child in widget.winfo_children():
                    bind_mousewheel_to_widget(child)
                return None
            except Exception:
                return None


        
        def on_content_configure(event = None):
            refresh_scroll_region()
            bind_mousewheel_to_widget(content)

        canvas.bind('<Configure>', on_canvas_configure)
        canvas.bind('<MouseWheel>', on_mousewheel, add = '+')
        canvas.bind('<Button-4>', on_mousewheel, add = '+')
        canvas.bind('<Button-5>', on_mousewheel, add = '+')
        content.bind('<Configure>', on_content_configure)
        bind_mousewheel_to_widget(content)
        return content

    
    def _build_ui(self):
        main_content = self._create_vertical_scroll_area(self)
        self._main_scroll_content = main_content
        self.active_program_var = tk.StringVar(value = self._active_program_summary())
        top = ttk.Frame(main_content, padding = 12)
        top.pack(fill = 'x')
        top_btn_row = ttk.Frame(top)
        top_btn_row.pack(fill = 'x', pady = (0, 8))
        tk.Button(top_btn_row, text = '저장', command = self._save, bg = '#f1f5f9', fg = '#0f172a', activebackground = '#e2e8f0', activeforeground = '#0f172a', relief = 'flat', padx = 14, pady = 4, cursor = 'hand2', font = ('', 9)).pack(side = 'left')
        tk.Button(top_btn_row, text = '불러오기', command = self._load, bg = '#f1f5f9', fg = '#0f172a', activebackground = '#e2e8f0', activeforeground = '#0f172a', relief = 'flat', padx = 14, pady = 4, cursor = 'hand2', font = ('', 9)).pack(side = 'left', padx = 8)
        tk.Button(top_btn_row, text = '설명서', command = self._show_help, bg = '#dbeafe', fg = '#1e3a8a', activebackground = '#bfdbfe', activeforeground = '#1e3a8a', relief = 'flat', padx = 14, pady = 4, cursor = 'hand2', font = ('', 9)).pack(side = 'left')
        tk.Button(top_btn_row, textvariable = self.active_program_var, command = self._open_active_program_dialog, bg = '#ecfeff', fg = '#155e75', activebackground = '#cffafe', activeforeground = '#155e75', relief = 'flat', padx = 14, pady = 4, cursor = 'hand2', font = ('', 9), anchor = 'w').pack(side = 'left', padx = (8, 0))
        hotkey_box = ttk.LabelFrame(top, text = '시작/종료/보조 키', padding = 10)
        hotkey_box.pack(fill = 'x')
        self.start_key_var = tk.StringVar(value = self._hotkey_list_summary(self.start_keys))
        self.stop_key_var = tk.StringVar(value = self._hotkey_list_summary(self.stop_keys))
        self.pause_key_var = tk.StringVar(value = self._pause_keys_summary())
        self.loot_key_var = tk.StringVar(value = hotkey_display_text(self.loot_hold_key_str))
        self.quick_right_key_var = tk.StringVar(value = hotkey_display_text(self.quick_right_hold_key_str))
        self.start_stop_same_var = tk.BooleanVar(value = bool(self.start_stop_same_key))
        self.center_status_var = tk.BooleanVar(value = bool(self.center_status_enabled))
        row = ttk.Frame(hotkey_box)
        row.pack(fill = 'x', pady = 4)
        ttk.Checkbutton(row, text = '시작/종료키 동일키 사용', variable = self.start_stop_same_var, command = self._toggle_start_stop_same_key).pack(side = 'left', padx = (0, 12))
        ttk.Label(row, text = '|').pack(side = 'left', padx = (0, 12))
        ttk.Label(row, text = '시작키').pack(side = 'left')
        ttk.Entry(row, textvariable = self.start_key_var, width = 24, state = 'readonly').pack(side = 'left', padx = 6)
        ttk.Button(row, text = '시작키 설정', command = self._set_start_key).pack(side = 'left', padx = 6)
        ttk.Label(row, text = '종료키').pack(side = 'left', padx = (18, 0))
        self.stop_key_entry = ttk.Entry(row, textvariable = self.stop_key_var, width = 24, state = 'readonly')
        self.stop_key_entry.pack(side = 'left', padx = 6)
        self.stop_key_button = ttk.Button(row, text = '종료키 설정', command = self._set_stop_key)
        self.stop_key_button.pack(side = 'left', padx = 6)
        center_status_row = ttk.Frame(row)
        center_status_row.pack(side = 'left', padx = (18, 0))
        ttk.Checkbutton(center_status_row, text = '화면 중앙 상태표시', variable = self.center_status_var, command = self._toggle_center_status_overlay).pack(side = 'left')
        ttk.Button(center_status_row, text = '설정', command = self._open_center_status_settings).pack(side = 'left', padx = (6, 0))
        row2 = ttk.Frame(hotkey_box)
        row2.pack(fill = 'x', pady = (8, 4))
        ttk.Label(row2, text = '일시정지키').pack(side = 'left')
        ttk.Entry(row2, textvariable = self.pause_key_var, width = 24, state = 'readonly').pack(side = 'left', padx = 6)
        ttk.Button(row2, text = '일시정지키 설정', command = self._set_pause_key).pack(side = 'left', padx = 6)
        ttk.Label(row2, text = '빨리줍기키').pack(side = 'left', padx = (18, 0))
        ttk.Entry(row2, textvariable = self.loot_key_var, width = 16, state = 'readonly').pack(side = 'left', padx = 6)
        ttk.Button(row2, text = '빨리줍기키 설정', command = self._set_loot_key).pack(side = 'left', padx = 6)
        ttk.Label(row2, text = '빠른우클릭키').pack(side = 'left', padx = (18, 0))
        ttk.Entry(row2, textvariable = self.quick_right_key_var, width = 16, state = 'readonly').pack(side = 'left', padx = 6)
        ttk.Button(row2, text = '빠른우클릭키 설정', command = self._set_quick_right_key).pack(side = 'left', padx = 6)
        self._sync_start_stop_same_key_ui()
        mid = ttk.Frame(main_content, padding = 12)
        mid.pack(fill = 'both', expand = True)
        list_box = ttk.LabelFrame(mid, text = '반복 키 목록', padding = 10)
        list_box.pack(fill = 'both', expand = True)
        cols = ('type', 'target', 'mode', 'interval')
        self.tree = ttk.Treeview(list_box, columns = cols, show = 'headings', selectmode = 'browse')
        self.tree.heading('type', text = '종류')
        self.tree.heading('target', text = '대상')
        self.tree.heading('mode', text = '동작')
        self.tree.heading('interval', text = '반복(초)')
        self.tree.column('type', width = 90, anchor = 'center')
        self.tree.column('target', width = 220, anchor = 'center')
        self.tree.column('mode', width = 90, anchor = 'center')
        self.tree.column('interval', width = 90, anchor = 'center')
        self.tree.pack(fill = 'both', expand = True, side = 'left')
        sc = ttk.Scrollbar(list_box, orient = 'vertical', command = self.tree.yview)
        self.tree.configure(yscrollcommand = sc.set)
        sc.pack(side = 'right', fill = 'y')
        btn_row = ttk.Frame(mid)
        btn_row.pack(fill = 'x', pady = (10, 0))
        ttk.Button(btn_row, text = '반복키추가', command = self._add_key_action).pack(side = 'left')
        ttk.Button(btn_row, text = '반복마우스추가', command = self._add_mouse_action).pack(side = 'left', padx = 8)
        ttk.Button(btn_row, text = '편집', command = self._edit_selected).pack(side = 'left', padx = 8)
        ttk.Button(btn_row, text = '삭제', command = self._delete_selected).pack(side = 'left', padx = 8)
        trigger_box = ttk.LabelFrame(mid, text = '자동 순차 실행 목록 - 특정 키/마우스 입력 후 지정키 순차 실행', padding = 10)
        trigger_box.pack(fill = 'both', expand = True, pady = (12, 0))
        trigger_cols = ('trigger', 'delay', 'target')
        self.trigger_tree = ttk.Treeview(trigger_box, columns = trigger_cols, show = 'headings', selectmode = 'browse')
        self.trigger_tree.heading('trigger', text = '시작 조건')
        self.trigger_tree.heading('delay', text = '실행 수')
        self.trigger_tree.heading('target', text = '실행 순서')
        self.trigger_tree.column('trigger', width = 240, anchor = 'center')
        self.trigger_tree.column('delay', width = 90, anchor = 'center')
        self.trigger_tree.column('target', width = 520, anchor = 'w')
        self.trigger_tree.pack(fill = 'both', expand = True, side = 'left')
        trigger_sc = ttk.Scrollbar(trigger_box, orient = 'vertical', command = self.trigger_tree.yview)
        self.trigger_tree.configure(yscrollcommand = trigger_sc.set)
        trigger_sc.pack(side = 'right', fill = 'y')
        trigger_btn_row = ttk.Frame(mid)
        trigger_btn_row.pack(fill = 'x', pady = (10, 0))
        ttk.Button(trigger_btn_row, text = '자동순차실행추가', command = self._add_trigger_action).pack(side = 'left')
        ttk.Button(trigger_btn_row, text = '자동순차실행편집', command = self._edit_trigger_selected).pack(side = 'left', padx = 8)
        ttk.Button(trigger_btn_row, text = '자동순차실행삭제', command = self._delete_trigger_selected).pack(side = 'left', padx = 8)
        bottom = ttk.Frame(self, padding = 12)
        bottom.pack(fill = 'x')
        status_wrap = ttk.Frame(bottom)
        status_wrap.pack(side = 'left', fill = 'x', expand = True)
        self.status_var = tk.StringVar(value = '대기중 (시작키를 누르면 반복 키/자동 순차 실행 시작, 종료키로 모두 중지)')
        indicator_bg = self.cget('bg')
        self.status_indicator_canvas = tk.Canvas(status_wrap, width = 18, height = 18, highlightthickness = 0, bd = 0, bg = indicator_bg)
        self.status_indicator_canvas.pack(side = 'left', padx = (0, 8))
        self.status_indicator_item = self.status_indicator_canvas.create_oval(2, 2, 16, 16, fill = '#d9534f', outline = '#b52b27', width = 1)
        ttk.Label(status_wrap, textvariable = self.status_var).pack(side = 'left')
        self.status_var.trace_add('write', self._refresh_status_indicator)
        self._refresh_status_indicator()
        self._schedule_status_indicator_refresh()
        self._refresh_tree()
        self._refresh_trigger_tree()

    
    def _center_child_window(self = None, win = None, width = None, height = None):
        win.update_idletasks()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        win_w = min(width, int(screen_w * 0.9))
        win_h = min(height, int(screen_h * 0.88))
        x = max(0, (screen_w - win_w) // 2)
        y = max(0, (screen_h - win_h) // 2)
        win.geometry(f'''{win_w}x{win_h}+{x}+{y}''')

    
    def _fit_window_to_content(self):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        max_w = int(screen_w * 0.97)
        max_h = int(screen_h * 0.88)
        min_w = min(1040, max_w)
        min_h = min(720, max_h)
        self.minsize(min_w, min_h)
        scroll_content = getattr(self, '_main_scroll_content', None)
        content_req_h = 0
        if scroll_content is not None:
            
            try:
                content_req_h = scroll_content.winfo_reqheight()
            except Exception:
                content_req_h = 0

            fixed_bottom_h = 54
            req_w = max(1240, self.winfo_reqwidth() + 24)
            req_h = max(780, self.winfo_reqheight() + 24, content_req_h + fixed_bottom_h + 24)
            win_w = min(req_w, max_w)
            win_h = min(req_h, max_h)
            x = max(0, (screen_w - win_w) // 2)
            y = max(0, (screen_h - win_h) // 2)
            self.geometry(f'''{win_w}x{win_h}+{x}+{y}''')
            return None

    
    def _status_indicator_mode(self = None):
        if self.paused_hold:
            return 'paused'
        if self._is_active_program_waiting():
            return 'target_blocked'
        if self.running or self.triggers_enabled or self.quick_click_active or self.loot_hold_active:
            return 'running'
        return 'stopped'

    
    def _status_indicator_colors(self):
        mode = self._status_indicator_mode()
        if mode == 'running':
            return ('#2ecc71', '#229954')
        if mode == 'paused':
            return ('#f8c471', '#d68910')
        if mode == 'target_blocked':
            return ('#64748b', '#475569')
        return ('#e74c3c', '#c0392b')

    
    def _refresh_status_indicator(self, *_, force = False):
        mode = self._status_indicator_mode()
        center_enabled = bool(getattr(self, 'center_status_enabled', False))
        if not getattr(self, 'center_status_targets', [
            'window']):
            getattr(self, 'center_status_targets', [
                'window'])
        targets_key = tuple([
            'window'])
        shape = getattr(self, 'center_status_shape', 'circle')
        show_text = bool(getattr(self, 'center_status_show_text', False))
        size_percent = int(getattr(self, 'center_status_size_percent', 100) or 100)
        rects_key = ()
        if center_enabled:
            
            try:
                rects_key = tuple(((int(item.get('left', 0)), int(item.get('top', 0)), int(item.get('right', 0)), int(item.get('bottom', 0))) for item in self._center_status_target_rects()))
            except Exception:
                rects_key = ()

            if force and mode == self._last_status_indicator_mode and center_enabled == self._last_center_status_enabled and targets_key == self._last_center_status_targets_key and rects_key == self._last_center_status_rects_key and shape == self._last_center_status_shape and show_text == self._last_center_status_show_text and size_percent == self._last_center_status_size_percent:
                return None
        self._last_status_indicator_mode = mode
        self._last_center_status_enabled = center_enabled
        self._last_center_status_targets_key = targets_key
        self._last_center_status_rects_key = rects_key
        self._last_center_status_shape = shape
        self._last_center_status_show_text = show_text
        self._last_center_status_size_percent = size_percent
        canvas = getattr(self, 'status_indicator_canvas', None)
        item = getattr(self, 'status_indicator_item', None)
        if canvas is not None and item is not None:
            (fill, outline) = self._status_indicator_colors()
            canvas.itemconfig(item, fill = fill, outline = outline)
        self._refresh_center_status_overlay(force = force)

    
    def _schedule_status_indicator_refresh(self):
        
        try:
            if self._status_refresh_after_id is not None:
                self.after_cancel(self._status_refresh_after_id)

            def refresh_loop():

                try:
                    self._enforce_active_program_guard()
                    self._refresh_status_indicator()
                    self._status_refresh_after_id = self.after(200, refresh_loop)
                    return None
                except Exception:
                    self._status_refresh_after_id = None
                    return None

            self._status_refresh_after_id = self.after(200, refresh_loop)
            return None
        except Exception:
            pass

    
    def _toggle_center_status_overlay(self):
        if hasattr(self, 'center_status_var'):
            self.center_status_enabled = bool(self.center_status_var.get())
        self._refresh_status_indicator(force = True)

    
    def _open_center_status_settings(self):
        CenterStatusSettingsDialog(self)

    
    def _normalize_active_program_targets(self = None, targets = None):
        raw_targets = targets if isinstance(targets, list) else []
        clean = []
        seen = set()
        for target in raw_targets:
            process_name = normalize_program_process_name(str(target or '').strip())
            if not process_name:
                continue
            key = process_name.lower()
            if key in seen:
                continue
            clean.append(process_name)
            seen.add(key)
        return clean

    
    def _active_program_summary(self = None):
        targets = self._normalize_active_program_targets(getattr(self, 'active_program_targets', []))
        if bool(getattr(self, 'active_program_all', True)) or not targets:
            return '동작시킬 프로그램: 전체 ▼'
        first = targets[0]
        if len(targets) == 1:
            return f'''동작시킬 프로그램: {first} ▼'''
        return f'''동작시킬 프로그램: {first} 외 {len(targets) - 1}개 ▼'''

    
    def _refresh_active_program_var(self):
        if hasattr(self, 'active_program_var'):
            self.active_program_var.set(self._active_program_summary())
            return None

    
    def _open_active_program_dialog(self):
        ActiveProgramDialog(self)

    
    def _is_active_program_allowed(self = None):
        targets = self._normalize_active_program_targets(getattr(self, 'active_program_targets', []))
        if bool(getattr(self, 'active_program_all', True)) or not targets:
            return True
        current_process = get_foreground_process_name()
        if not current_process:
            return False
        target_set = {target.lower() for target in targets}
        return current_process.lower() in target_set
        

    
    def _is_active_program_restricted(self = None):
        targets = self._normalize_active_program_targets(getattr(self, 'active_program_targets', []))
        return not bool(getattr(self, 'active_program_all', True)) and bool(targets)

    
    def _is_active_program_waiting(self = None):
        if self.paused_hold:
            return False
        if not self.running and not self.triggers_enabled and not self.quick_click_active and not self.loot_hold_active:
            return False
        if not self._is_active_program_restricted():
            return False
        return not self._is_active_program_allowed()

    
    def _macro_active_status_message(self = None):
        if self.quick_click_active or self.loot_hold_active:
            if self.quick_click_button == 'right':
                if self.running or self._loot_triggers_enabled_before:
                    return '빠른우클릭중 (기존 매크로 임시정지, 빠른우클릭키를 떼면 재개)'
                return '빠른우클릭중 (우클릭 반복, 빠른우클릭키를 떼면 정지)'
            if self.running or self._loot_triggers_enabled_before:
                return '루팅중 (기존 매크로 임시정지, 루팅키를 떼면 재개)'
            return '루팅중 (좌클릭 반복, 루팅키를 떼면 정지)'
        if self.paused_hold:
            return '일시정지중 (반복 키/자동 순차 실행 모두 중지, 일시정지키를 모두 떼면 재개)'
        if self.running and self.triggers_enabled:
            return '실행중 (반복 키/자동 순차 실행 활성화, 종료키로 모두 중지)'
        if self.running:
            return '실행중 (반복 키만 활성화, 종료키로 중지)'
        if self.triggers_enabled:
            return '자동 순차 실행 활성화중 (종료키로 중지)'
        return '대기중 (시작키를 누르면 반복 키/자동 순차 실행 시작, 종료키로 모두 중지)'

    
    def _enforce_active_program_guard(self = None):
        restricted = self._is_active_program_restricted()
        if not restricted:
            if self._active_program_blocked:
                self._active_program_blocked = False
                if self.running and not self.paused_hold and not self.loot_hold_active and not self._is_input_blocked():
                    for action in self.actions:
                        if not action.get('mode') == 'hold':
                            continue
                        self._apply_hold_start(action)
                if hasattr(self, 'status_var'):
                    self.status_var.set(self._macro_active_status_message())
            return True
        allowed = self._is_active_program_allowed()
        if allowed:
            if self._active_program_blocked:
                self._active_program_blocked = False
                if self.running and not self.paused_hold and not self.loot_hold_active and not self._is_input_blocked():
                    for action in self.actions:
                        if not action.get('mode') == 'hold':
                            continue
                        self._apply_hold_start(action)
                if hasattr(self, 'status_var'):
                    self.status_var.set(self._macro_active_status_message())
            return True
        if not self._active_program_blocked:
            self._active_program_blocked = True
            with self._trigger_lock:
                self._pressed_trigger_keys.clear()
                self._pressed_trigger_mouse_inputs.clear()
                self._suppressed_trigger_inputs.clear()
            self._apply_hold_stop()
            if hasattr(self, 'status_var'):
                self.status_var.set('동작 프로그램 대기중 (선택한 프로그램 창에서만 매크로가 동작합니다)')
        return False

    
    def _on_main_window_configure(self, event = (None,)):
        if event is not None and getattr(event, 'widget', None) is not self:
            return None
        if not bool(getattr(self, 'center_status_enabled', False)):
            return None
        
        try:
            if self._center_overlay_reposition_after_id is not None:
                self.after_cancel(self._center_overlay_reposition_after_id)

            def reposition_overlay():
                self._center_overlay_reposition_after_id = None

                try:
                    self._refresh_status_indicator(force = True)
                    return None
                except Exception:
                    return None

            self._center_overlay_reposition_after_id = self.after(250, reposition_overlay)
            return None
        except Exception:
            pass

    
    def _default_center_status_target(self = None):
        monitors = self._enumerate_display_monitors()
        for monitor in monitors:
            if not monitor.get('primary'):
                continue
            
            return monitors, monitor.get('target', 'monitor:0')
        if monitors:
            return monitors[0].get('target', 'monitor:0')
        return 'monitor:0'

    
    def _normalize_center_status_targets(self = None, targets = None):
        raw_targets = targets if targets is not None else getattr(self, 'center_status_targets', [
            'monitor:0'])
        if not isinstance(raw_targets, list):
            raw_targets = [
                'monitor:0']
        monitors = self._enumerate_display_monitors()
        valid_targets = {str(monitor.get('target', '')) for monitor in monitors}
        default_target = self._default_center_status_target()
        clean = []
        seen = set()
        for target in raw_targets:
            target = str(target or '').strip()
            if not target:
                continue
            if target == 'window':
                target = default_target
            if not target.startswith('monitor:'):
                continue
            if valid_targets and target not in valid_targets:
                continue
            if target in seen:
                continue
            clean.append(target)
            seen.add(target)
        if clean:
            return clean
        return [
            default_target]
        

    
    def _center_status_size_percent_value(self = None):
        
        try:
            value = int(getattr(self, 'center_status_size_percent', 100))
        except Exception:
            value = 100

        return max(50, min(200, value))

    
    def _center_status_text(self = None):
        mode = self._status_indicator_mode()
        if mode == 'running':
            return '실행중'
        if mode == 'paused':
            return '일시정지'
        if mode == 'target_blocked':
            return '대상아님'
        return '대기중'

    
    def _enumerate_display_monitors(self = None):
        monitors = []
        if sys.platform.startswith('win'):
            
            try:
                
                class RECT(ctypes.Structure):
                    _fields_ = [
                        ('left', ctypes.c_long),
                        ('top', ctypes.c_long),
                        ('right', ctypes.c_long),
                        ('bottom', ctypes.c_long)]

                
                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', ctypes.c_ulong),
                        ('rcMonitor', RECT),
                        ('rcWork', RECT),
                        ('dwFlags', ctypes.c_ulong)]
                user32 = ctypes.windll.user32
                monitor_enum_proc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(RECT), ctypes.c_void_p)
                user32.EnumDisplayMonitors.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    monitor_enum_proc,
                    ctypes.c_void_p]
                user32.EnumDisplayMonitors.restype = ctypes.c_bool
                user32.GetMonitorInfoW.argtypes = [
                    ctypes.c_void_p,
                    ctypes.POINTER(MONITORINFO)]
                user32.GetMonitorInfoW.restype = ctypes.c_bool
                
                def callback(hmonitor = None, hdc = None, lprc_monitor = None, dw_data = None):
                    info = MONITORINFO()
                    info.cbSize = ctypes.sizeof(MONITORINFO)
                    if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                        rect = info.rcMonitor
                        monitors.append({
                            'target': f'''monitor:{len(monitors)}''',
                            'label': f'''모니터 {len(monitors) + 1}''',
                            'left': int(rect.left),
                            'top': int(rect.top),
                            'right': int(rect.right),
                            'bottom': int(rect.bottom),
                            'primary': bool(info.dwFlags & 1) })
                    return 1

                enum_proc = monitor_enum_proc(callback)
                user32.EnumDisplayMonitors(None, None, enum_proc, None)
            except Exception:
                monitors = []

            if not monitors:
                
                try:
                    screen_w = self.winfo_screenwidth()
                    screen_h = self.winfo_screenheight()
                except Exception:
                    screen_w = 1920
                    screen_h = 1080

                monitors = [
                    {
                        'target': 'monitor:0',
                        'label': '모니터 1',
                        'left': 0,
                        'top': 0,
                        'right': int(screen_w),
                        'bottom': int(screen_h),
                        'primary': True }]
        return monitors

    
    def _window_monitor_rect(self = None):
        if sys.platform.startswith('win'):
            
            try:
                self.update_idletasks()
                hwnd = self.winfo_id()
                
                class RECT(ctypes.Structure):
                    _fields_ = [
                        ('left', ctypes.c_long),
                        ('top', ctypes.c_long),
                        ('right', ctypes.c_long),
                        ('bottom', ctypes.c_long)]

                
                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ('cbSize', ctypes.c_ulong),
                        ('rcMonitor', RECT),
                        ('rcWork', RECT),
                        ('dwFlags', ctypes.c_ulong)]
                user32 = ctypes.windll.user32
                monitor_default_to_nearest = 2
                monitor = user32.MonitorFromWindow(hwnd, monitor_default_to_nearest)
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    rect = info.rcMonitor
                    return {
                        'target': 'window',
                        'label': '프로그램 실행창 기준',
                        'left': int(rect.left),
                        'top': int(rect.top),
                        'right': int(rect.right),
                        'bottom': int(rect.bottom),
                        'primary': bool(info.dwFlags & 1) }
            except Exception:
                pass

            monitors = self._enumerate_display_monitors()
            if monitors:
                item = dict(monitors[0])
                item['target'] = 'window'
                item['label'] = '프로그램 실행창 기준'
                return item
            return {
                'target': 'window',
                'label': '프로그램 실행창 기준',
                'left': 0,
                'top': 0,
                'right': 1920,
                'bottom': 1080,
                'primary': True }

    
    def _center_status_target_rects(self = None):
        targets = self._normalize_center_status_targets()
        monitors = self._enumerate_display_monitors()
        monitor_by_target = {m['target']: m for m in monitors}
        rects = []
        seen_rects = set()
        for target in targets:
            if target == 'window':
                item = self._window_monitor_rect()
            else:
                item = monitor_by_target.get(target)
                if item is None:
                    continue
            rect_key = (item['left'], item['top'], item['right'], item['bottom'])
            if rect_key in seen_rects:
                continue
            rects.append(dict(item))
            seen_rects.add(rect_key)
        if not rects:
            rects.append(self._window_monitor_rect())
        return rects
        

    
    def _center_status_scaled_value(self = None, base_value = None):
        size_percent = self._center_status_size_percent_value()
        return max(1, int(round(base_value * size_percent / 100)))

    
    def _center_overlay_circle_size(self = None, monitor_rect = None):
        
        try:
            if monitor_rect:
                monitor_w = max(1, int(monitor_rect['right']) - int(monitor_rect['left']))
                monitor_h = max(1, int(monitor_rect['bottom']) - int(monitor_rect['top']))
            else:
                monitor_w = self.winfo_screenwidth()
                monitor_h = self.winfo_screenheight()
            base_size = int(min(monitor_w, monitor_h) * 0.014)
        except Exception:
            base_size = 14

        base_size = max(10, min(14, base_size))
        return max(6, self._center_status_scaled_value(base_size))

    
    def _center_overlay_bar_size(self = None, monitor_rect = None):
        base_width = 84
        base_height = 12
        return (self._center_status_scaled_value(base_width), self._center_status_scaled_value(base_height))

    
    def _center_overlay_text_height(self = None):
        if not bool(getattr(self, 'center_status_show_text', False)):
            return 0
        return max(14, self._center_status_scaled_value(15))

    
    def _center_overlay_font_size(self = None):
        return max(9, self._center_status_scaled_value(11))

    
    def _center_overlay_font_family(self = None):
        
        try:
            available_fonts = set(tkfont.families(self))
        except Exception:
            pass

        preferred_fonts = [
            'HY헤드라인M',
            'HYHeadLine-Medium',
            'Arial Black',
            'Gulim',
            'Dotum',
            'Malgun Gothic']
        for font_name in preferred_fonts:
            if not font_name in available_fonts:
                continue
            
            return font_name
        return 'Gulim'

    
    def _center_overlay_text_font(self = None):
        font_family = self._center_overlay_font_family()
        font_size = self._center_overlay_font_size()
        already_bold_fonts = {
            'HY헤드라인M',
            'Arial Black',
            'HYHeadLine-Medium'}
        if font_family in already_bold_fonts:
            return (font_family, font_size)
        return (font_family, font_size, 'bold')

    
    def _center_overlay_window_size(self = None, monitor_rect = None):
        show_text = bool(getattr(self, 'center_status_show_text', False))
        shape = getattr(self, 'center_status_shape', 'circle')
        if shape == 'bar':
            (shape_w, shape_h) = self._center_overlay_bar_size(monitor_rect)
            width = shape_w + 12
            height = shape_h + 8
        else:
            circle_size = self._center_overlay_circle_size(monitor_rect)
            width = circle_size + 8
            height = circle_size + 8
        if show_text:
            text_width = max(54, self._center_status_scaled_value(54))
            width = max(width, text_width)
            height += self._center_overlay_text_height() + 2
        return (max(1, width), max(1, height))

    
    def _center_overlay_geometry_for_rect(self = None, monitor_rect = None):
        (width, height) = self._center_overlay_window_size(monitor_rect)
        monitor_left = int(monitor_rect.get('left', 0))
        monitor_top = int(monitor_rect.get('top', 0))
        monitor_right = int(monitor_rect.get('right', 1920))
        monitor_bottom = int(monitor_rect.get('bottom', 1080))
        monitor_w = max(1, monitor_right - monitor_left)
        monitor_h = max(1, monitor_bottom - monitor_top)
        x = monitor_left + max(0, (monitor_w - width) // 2)
        y = monitor_top + max(0, (monitor_h - height) // 2)
        return f'''{width}x{height}+{x}+{y}'''

    
    def _draw_center_overlay_content(self = None, entry = None):
        canvas = entry.get('canvas')
        text_label = entry.get('text_label')
        monitor_rect = entry.get('monitor_rect') or { }
        if canvas is None:
            return None
        shape = getattr(self, 'center_status_shape', 'circle')
        show_text = bool(getattr(self, 'center_status_show_text', False))
        (fill, outline) = self._status_indicator_colors()
        (width, height) = self._center_overlay_window_size(monitor_rect)
        transparent_color = self.center_status_transparent_color
        
        try:
            shape_height = height
            if show_text:
                shape_height = max(1, height - self._center_overlay_text_height() - 2)
            canvas.configure(width = width, height = shape_height, bg = transparent_color)
            canvas.delete('all')
            if shape == 'bar':
                (bar_w, bar_h) = self._center_overlay_bar_size(monitor_rect)
                x1 = max(2, (width - bar_w) // 2)
                y1 = max(3, (shape_height - bar_h) // 2)
                x2 = x1 + bar_w
                y2 = y1 + bar_h
                canvas.create_rectangle(x1, y1, x2, y2, fill = fill, outline = outline, width = 1)
            else:
                circle_size = self._center_overlay_circle_size(monitor_rect)
                x1 = max(2, (width - circle_size) // 2)
                y1 = max(3, (shape_height - circle_size) // 2)
                x2 = x1 + circle_size
                y2 = y1 + circle_size
                canvas.create_oval(x1, y1, x2, y2, fill = fill, outline = outline, width = 1)
            if text_label is not None:
                if show_text:
                    text_label.configure(text = self._center_status_text(), fg = fill, bg = transparent_color, font = self._center_overlay_text_font())
                    text_label.pack(side = 'top', fill = 'x')
                    return None
                text_label.pack_forget()
                return None
        except Exception:
            return None

    
    def _apply_center_overlay_click_through(self = None, overlay = None, canvas = None):
        if overlay is None:
            overlay = getattr(self, 'center_status_overlay', None)
        if canvas is None:
            canvas = getattr(self, 'center_status_canvas', None)
        if overlay is None:
            return False
        if not sys.platform.startswith('win'):
            return True
        
        try:
            overlay.update_idletasks()
            overlay_hwnd = int(overlay.winfo_id())
            canvas_hwnd = int(canvas.winfo_id()) if canvas is not None else 0
            user32 = ctypes.windll.user32
            gwl_exstyle = -20
            ga_root = 2
            ws_ex_layered = 524288
            ws_ex_transparent = 32
            ws_ex_toolwindow = 128
            ws_ex_noactivate = 134217728
            lwa_colorkey = 1
            lwa_alpha = 2
            swp_nosize = 1
            swp_nomove = 2
            swp_nozorder = 4
            swp_framechanged = 32
            
            try:
                get_window_long = user32.GetWindowLongPtrW
                set_window_long = user32.SetWindowLongPtrW
                get_window_long.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_int]
                get_window_long.restype = ctypes.c_ssize_t
                set_window_long.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_int,
                    ctypes.c_ssize_t]
                set_window_long.restype = ctypes.c_ssize_t
            except AttributeError:
                get_window_long = user32.GetWindowLongW
                set_window_long = user32.SetWindowLongW
                get_window_long.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_int]
                get_window_long.restype = ctypes.c_long
                set_window_long.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_int,
                    ctypes.c_long]
                set_window_long.restype = ctypes.c_long
            user32.GetAncestor.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint]
            user32.GetAncestor.restype = ctypes.c_void_p
            user32.SetLayeredWindowAttributes.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_ubyte,
                ctypes.c_uint32]
            user32.SetLayeredWindowAttributes.restype = ctypes.c_bool
            user32.SetWindowPos.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint]
            user32.SetWindowPos.restype = ctypes.c_bool
            user32.EnableWindow.argtypes = [
                ctypes.c_void_p,
                ctypes.c_bool]
            user32.EnableWindow.restype = ctypes.c_bool
            user32.IsWindowEnabled.argtypes = [
                ctypes.c_void_p]
            user32.IsWindowEnabled.restype = ctypes.c_bool
            
            try:
                overlay.attributes('-disabled', True)
            except Exception:
                pass
            root_hwnd = int(user32.GetAncestor(ctypes.c_void_p(overlay_hwnd), ga_root) or overlay_hwnd)
            transparent_color = self.center_status_transparent_color.lstrip('#')
            red = int(transparent_color[0:2], 16)
            green = int(transparent_color[2:4], 16)
            blue = int(transparent_color[4:6], 16)
            colorref = red | green << 8 | blue << 16
            target_hwnds = []
            for target_hwnd in (root_hwnd, overlay_hwnd, canvas_hwnd):
                if not target_hwnd:
                    continue
                if target_hwnd in target_hwnds:
                    continue
                target_hwnds.append(target_hwnd)
            applied_results = []
            for target_hwnd in target_hwnds:
                user32.EnableWindow(ctypes.c_void_p(target_hwnd), False)
                ex_style = int(get_window_long(ctypes.c_void_p(target_hwnd), gwl_exstyle) or 0)
                ex_style = ex_style | ws_ex_layered | ws_ex_transparent | ws_ex_toolwindow | ws_ex_noactivate
                set_window_long(ctypes.c_void_p(target_hwnd), gwl_exstyle, ex_style)
                user32.SetLayeredWindowAttributes(ctypes.c_void_p(target_hwnd), colorref, 255, lwa_colorkey | lwa_alpha)
                user32.SetWindowPos(ctypes.c_void_p(target_hwnd), 0, 0, 0, 0, 0, swp_nomove | swp_nosize | swp_nozorder | swp_framechanged)
                applied_style = int(get_window_long(ctypes.c_void_p(target_hwnd), gwl_exstyle) or 0)
                has_layered = bool(applied_style & ws_ex_layered)
                has_transparent = bool(applied_style & ws_ex_transparent)
                is_disabled = not bool(user32.IsWindowEnabled(ctypes.c_void_p(target_hwnd)))
                applied_results.append((target_hwnd, has_layered, has_transparent, is_disabled))
            overlay.update_idletasks()
            root_result = next((x for x in applied_results if x[0] == root_hwnd), None)
            overlay_result = next((x for x in applied_results if x[0] == overlay_hwnd), None)
            root_ok = bool(root_result and root_result[1] and root_result[2] and root_result[3])
            overlay_ok = bool(overlay_result and overlay_result[1] and overlay_result[2] and overlay_result[3])
            return root_ok and overlay_ok
        except Exception:
            return False


    
    def _destroy_center_status_overlays(self):
        overlays = getattr(self, 'center_status_overlays', { }) or { }
        for entry in list(overlays.values()):
            overlay = entry.get('overlay')
            if overlay is None:
                continue
            try:
                overlay.destroy()
            except Exception:
                continue
        self.center_status_overlays = { }
        return None


    def _disable_center_status_overlay_for_safety(self):
        self.center_status_enabled = False
        if hasattr(self, 'center_status_var'):
            try:
                self.center_status_var.set(False)
            except Exception:
                pass
        self._destroy_center_status_overlays()
        self._last_center_status_enabled = None
        return None

    
    def _schedule_center_overlay_click_through_retry(self = None, overlay_key = None, attempt = None):
        if not bool(getattr(self, 'center_status_enabled', False)):
            return None
        if attempt > 5:
            retry_entries = []
            if overlay_key is not None:
                entry = self.center_status_overlays.get(overlay_key)
                if entry:
                    retry_entries.append((overlay_key, entry))
                else:
                    retry_entries.extend(list(self.center_status_overlays.items()))
            for key, entry in retry_entries:
                overlay = entry.get('overlay')
                if overlay is None:
                    continue
                overlay.deiconify()
                overlay.lift()
                overlay.attributes('-topmost', True)
                overlay.update_idletasks()
            return None
        
        try:
            if self._center_overlay_click_through_retry_after_id is not None:
                self.after_cancel(self._center_overlay_click_through_retry_after_id)

            def retry_click_through():
                try:
                    self._center_overlay_click_through_retry_after_id = None
                    if not bool(getattr(self, 'center_status_enabled', False)):
                        return None
                    retry_entries = []
                    if overlay_key is not None:
                        entry_now = self.center_status_overlays.get(overlay_key)
                        if entry_now:
                            retry_entries.append((overlay_key, entry_now))
                        else:
                            retry_entries.extend(list(self.center_status_overlays.items()))
                    for key, entry_now in retry_entries:
                        overlay_now = entry_now.get('overlay')
                        canvas_now = entry_now.get('canvas')
                        if overlay_now is None:
                            continue
                        if not overlay_now.winfo_exists():
                            continue
                        overlay_now.deiconify()
                        overlay_now.lift()
                        overlay_now.attributes('-topmost', True)
                        overlay_now.update_idletasks()
                        if self._apply_center_overlay_click_through(overlay_now, canvas_now):
                            continue
                        self._schedule_center_overlay_click_through_retry(key, attempt + 1)
                    return None
                except Exception:
                    pass

            delay_ms = min(150 * attempt, 600)
            self._center_overlay_click_through_retry_after_id = self.after(delay_ms, retry_click_through)
            return None
        except Exception:
            pass

    
    def _ensure_center_status_overlay(self = None, overlay_key = None, monitor_rect = None):
        overlays = getattr(self, 'center_status_overlays', { }) or { }
        entry = overlays.get(overlay_key)
        if entry is not None:
            overlay = entry.get('overlay')
            try:
                if overlay is not None and overlay.winfo_exists():
                    entry['monitor_rect'] = dict(monitor_rect)
                    return entry
            except Exception:
                pass

            transparent_color = self.center_status_transparent_color
            (width, height) = self._center_overlay_window_size(monitor_rect)
            overlay = tk.Toplevel()
            overlay.withdraw()
            overlay.overrideredirect(True)
            overlay.configure(bg = transparent_color)
            overlay.resizable(False, False)
            overlay.geometry(self._center_overlay_geometry_for_rect(monitor_rect))
            
            try:
                overlay.attributes('-topmost', True)
            except Exception:
                pass
            try:
                overlay.attributes('-transparentcolor', transparent_color)
            except Exception:
                pass
            canvas = tk.Canvas(overlay, width = width, height = height, highlightthickness = 0, bd = 0, bg = transparent_color)
            canvas.pack(side = 'top', fill = 'x')
            text_label = tk.Label(overlay, text = '', bg = transparent_color, fg = '#ffffff', bd = 0, highlightthickness = 0, padx = 0, pady = 0, font = self._center_overlay_text_font())
            entry = {
                'overlay': overlay,
                'canvas': canvas,
                'text_label': text_label,
                'monitor_rect': dict(monitor_rect) }
            self.center_status_overlays[overlay_key] = entry
            
            try:
                self._draw_center_overlay_content(entry)
                self._apply_center_overlay_click_through(overlay, canvas)
                overlay.deiconify()
                overlay.lift()
                overlay.attributes('-topmost', True)
                overlay.update_idletasks()
                overlay.update()
            except Exception:
                pass
            if not self._apply_center_overlay_click_through(overlay, canvas):
                self._schedule_center_overlay_click_through_retry(overlay_key)
        return entry

    
    def _refresh_center_status_overlay(self = None, force = None):
        enabled = bool(getattr(self, 'center_status_enabled', False))
        if not enabled:
            self._destroy_center_status_overlays()
            return None
        rects = self._center_status_target_rects()
        wanted_keys = set()
        try:
            for idx, monitor_rect in enumerate(rects):
                rect_key = (int(monitor_rect.get('left', 0)), int(monitor_rect.get('top', 0)), int(monitor_rect.get('right', 0)), int(monitor_rect.get('bottom', 0)))
                overlay_key = f'''{rect_key[0]}:{rect_key[1]}:{rect_key[2]}:{rect_key[3]}'''
                wanted_keys.add(overlay_key)
                entry = self._ensure_center_status_overlay(overlay_key, monitor_rect)
                overlay = entry.get('overlay')
                if overlay is None:
                    continue
                overlay.geometry(self._center_overlay_geometry_for_rect(monitor_rect))
                self._draw_center_overlay_content(entry)
                overlay.deiconify()
                overlay.lift()
                overlay.attributes('-topmost', True)
                overlay.update_idletasks()
                if force and not self._apply_center_overlay_click_through(overlay, entry.get('canvas')):
                    self._schedule_center_overlay_click_through_retry(overlay_key)
            overlays = getattr(self, 'center_status_overlays', { }) or { }
            for stale_key in list(overlays.keys()):
                if stale_key in wanted_keys:
                    continue
                entry = overlays.pop(stale_key, None)
                if not entry:
                    continue
                if entry.get('overlay') is None:
                    continue
                entry['overlay'].destroy()
            return None
        except Exception:
            pass

    
    def _show_help(self):
        self._begin_input_block()
        win = tk.Toplevel(self)
        win.title('매크로 사용 설명서')
        win.geometry('760x680')
        win.minsize(620, 520)
        win.resizable(True, True)
        win.transient(self)
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        win_w = min(760, int(screen_w * 0.9))
        win_h = min(680, int(screen_h * 0.88))
        x = max(0, (screen_w - win_w) // 2)
        y = max(0, (screen_h - win_h) // 2)
        win.geometry(f'''{win_w}x{win_h}+{x}+{y}''')
        root = ttk.Frame(win, padding = 12)
        root.pack(fill = 'both', expand = True)
        title = ttk.Label(root, text = '매크로 사용 설명서', font = ('', 14, 'bold'))
        title.pack(anchor = 'w', pady = (0, 10))
        text_frame = ttk.Frame(root)
        text_frame.pack(fill = 'both', expand = True)
        help_text = tk.Text(text_frame, wrap = 'word', font = ('', 10), padx = 12, pady = 12, height = 24, relief = 'solid', borderwidth = 1)
        help_text.pack(side = 'left', fill = 'both', expand = True)
        sc = ttk.Scrollbar(text_frame, orient = 'vertical', command = help_text.yview)
        help_text.configure(yscrollcommand = sc.set)
        sc.pack(side = 'right', fill = 'y')
        help_text.insert('1.0', '매크로 사용 설명서\n\n        1. 시작키 / 종료키 / 일시정지키 / 빨리줍기키\n\n        ◆시작/종료키 동일키 사용 체크\n        - 체크시 동일한 키로 시작/종료 가능합니다\n        - 예시) F1으로 설정시 F1 누를 때마다 시작/종료 반복\n\n        ◆시작키\n        - 시작키를 누르면 등록된 기능이 실행됩니다.\n        - 기본 시작키는 F1입니다(여러가지 키 추가 가능)\n\n        ◆종료키\n        - 종료키를 누르면 실행 중인 기능이 모두 꺼집니다.\n        - 기본 종료키는 F2입니다(여러가지 키 추가 가능)\n\n        ◆화면 중앙 상태표시\n        - 동작중(초록색), 일시정지(주황색), 대기중(빨간색)\n        - 설정 진입시 표시할 모니터, 표시방식, 크기 설정 가능\n\n        ◆일시정지키\n        - 일시정지키는 홀드, 토글 방식중 선택 가능 합니다\n          << 홀드 : 누르고 있어야 일시 정지됨 / 토글 : 한번누르면 일시정지 다시 누르면 동작\n        - 일시정지키는 더추가할수있습니다 ex) tab(지도), C(소지품창), T(귀환) 등등\n\n        ◆빨리줍기키\n        - 누르고 있는동안 빠르게 마우스 좌클릭 동작 됩니다\n        - 누르고 있는동안 일시정지키와 동일하게 모든 동작 일시 정지 됩니다\n        - 기본 빨리줍기키는 F3입니다.\n\n        ◆빠른우클릭키\n        - 누르고 있는동안 빠르게 마우스 우클릭 동작 됩니다\n        - 누르고 있는동안 일시정지키와 동일하게 모든 동작 일시 정지 됩니다\n        - 기본 빠른우클릭키는 F4입니다.\n\n=================================================\n\n        2. 반복 키\n\n        ◆반복 키는 시작키를 누른 뒤, 등록된 키나 마우스 \n        동작을 반복 실행하는 기능입니다.\n\n        ◆클릭(반복)\n        - 설정한 시간마다 키 또는 마우스를 반복해서 누릅니다.\n\n        ◆누르기(홀드)\n        - 키 또는 마우스를 계속 누른 상태로 유지합니다.\n\n=================================================\n\n        3. 자동 순차 실행\n\n        ◆자동 순차 실행은 특정 키나 마우스를 눌렀을 때\n        등록한 실행 목록을 자동으로 1번 실행하거나 반복 실행하는 기능입니다.\n\n        ◆중요:\n        - 한 번 누르면 실행 목록이 1번만 실행됩니다.\n        - 반복 실행은 실행 형태에서 반복실행을 선택하면 사용할 수 있습니다.\n        - 시작키를 누르고 있는 상태에서도 동작되게 설정 가능\n\n        ◆자동 순차 실행 예시(시작키 누를 때마다 실행)\n        설정:\n        시작키: 키 1\n\n        실행할 동작:\n        0.5초 후 → 2키\n        0.6초 후 → 3키\n        1.2초 후 → 마우스 왼쪽버튼\n\n        동작:\n        1번키를 한 번 누름\n        → 0.5초 후 2키 1번 실행\n        → 0.6초 후 3키 1번 실행\n        → 1.2초 후 좌클릭 1번 실행\n        → 종료\n\n        ◆자동 순차 실행 예시(반복실행)\n        설정:\n        시작키: 키 1\n\n        실행할 동작:\n        0.5초 후 → 2키\n        0.6초 후 → 3키\n        1.2초 후 → 마우스 왼쪽버튼\n\n        동작:\n        1번키를 한 번 누름\n        → 0.5초 후 2키 1번 실행\n        → 0.6초 후 3키 1번 실행\n        → 1.2초 후 좌클릭 1번 실행\n        → 2키 → 3키 → 좌클릭 반복 실행\n\n        ※ 만약 시작키를 매 반복 첫 동작에 포함으로 체크했다면\n        1번키를 한 번 누름\n        → 0.5초 후 2키 1번 실행\n        → 0.6초 후 3키 1번 실행\n        → 1.2초 후 좌클릭 1번 실행\n        → 1키 → 2키 → 3키 → 좌클릭 반복 실행\n        << 이렇게 시작키도 반복실행 첫 단계에 포함됩니다.\n\n        ◆자동 순차 실행 예시(시작키 누르고 있는 동안 동작)\n        설정:\n        시작키: 키 1\n\n        실행할 동작:\n        0.5초 후 → 2키\n        0.6초 후 → 3키\n        1.2초 후 → 마우스 왼쪽버튼\n\n        동작:\n        1번키를 누르고 있는 상태에서\n        → 0.5초 후 2키 1번 실행\n        → 0.6초 후 3키 1번 실행\n        → 1.2초 후 좌클릭 1번 실행\n        → 2키 → 3키 → 좌클릭 반복 실행\n\n=================================================\n\n        4. 시간 계산 방식\n\n        ◆자동 순차 실행의 시간은 처음 시작키를 \n        누른 순간 기준으로 계산됩니다.\n\n        예시)\n        시작키: 키 1\n\n        실행할 동작:\n        0.5초 후 → 2키\n        0.6초 후 → 3키\n\n        동작 기준:\n        1번키를 누른 순간 기준 0.5초 후 2키\n        1번키를 누른 순간 기준 0.6초 후 3키\n\n        즉, 0.6초 후 3키는 2키 실행 후 0.6초가 아닙니다.\n        1번키를 누른 순간부터 0.6초 후입니다.\n\n        그래서 위 예시에서 2키와  3키 사이 간격은 약 0.1초입니다.\n\n=================================================\n\n        5. 자동 순차 실행 - 실행 형태 / 실행 방식\n\n        ◆실행 형태\n        - 시작키 누를 때마다 실행 : 시작키를 누를 때마다 정해진 순서를 1번 실행합니다.\n\n        - 반복실행 : 시작키를 누르면 정해진 순서를 계속 반복합니다.\n          오른쪽 체크박스를 선택하면 시작키도 매 반복 첫 동작에 같이 실행됩니다.\n          종료키 또는 일시정지키로 멈출 수 있습니다.\n\n        - 시작키 누르고 있는 동안 실행 : 시작키를 누르고 있는 동안 순차실행 동작\n\n        ◆실행 방식\n        - 무조건실행 : 시작키를 누를 때마다 등록된 순차 실행이 발동됩니다.\n          >> 기존 순차실행 삭제후 실행 : 기존 순차실행 스케줄을 리셋하고 새로 실행합니다.\n          >> 기존 순차실행 유지후 추가실행 : 기존 순차실행 스케줄은 유지하고 추가로 실행합니다.\n\n        - 순차진행중미실행 : 순차 실행이 돌고 있는 중이라면 시작키를 눌러도 무시됩니다.\n\n        - 순차진행중 중단 여부\n          >> 시작키 누르고 있는 동안 실행의 전용 세부 설정 입니다\n          >> 시작키 떼면 동작 중이던 순차실행 중지 : 시작키 떼는 순간 모든 순차스케쥴 즉시 종료\n          >> 시작키 떼면 동작 중이던 순차실행 완료 후 중지 : 시작키 떼면 순차실행 남은것까지만 실행 후 종료\n        ')
        help_text.tag_configure('help_body', spacing1 = 1, spacing2 = 2, spacing3 = 5)
        help_text.tag_add('help_body', '1.0', 'end')
        help_text.tag_configure('help_section_title', font = ('', 10, 'bold'), spacing1 = 8, spacing3 = 6)
        for section_title in ('1. 시작키 / 종료키 / 일시정지키', '2. 반복 키', '3. 자동 순차 실행', '4. 시간 계산 방식', '5. 자동 순차 실행 - 실행 형태 / 실행 방식'):
            start_index = help_text.search(section_title, '1.0', stopindex = 'end')
            if not start_index:
                continue
            help_text.tag_add('help_section_title', start_index, f'''{start_index} lineend''')
        help_text.configure(state = 'disabled')
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (10, 0))
        help_closed_ref = {
            'closed': False }
        
        def close_help():
            if help_closed_ref['closed']:
                return None
            help_closed_ref['closed'] = True
            self._end_input_block()
            
            try:
                win.destroy()
                return None
            except Exception:
                return None


        win.protocol('WM_DELETE_WINDOW', close_help)
        tk.Button(btns, text = '닫기', command = close_help, bg = '#334155', fg = 'white', activebackground = '#1e293b', activeforeground = 'white', relief = 'flat', padx = 18, pady = 5, cursor = 'hand2', font = ('', 9, 'bold')).pack(side = 'right')

    
    def _suppress_next_trigger_input(self = None, trigger_type = None, trigger_value = None):
        key = f'''{trigger_type}:{trigger_value}'''
        with self._trigger_lock:
            self._suppressed_trigger_inputs[key] = self._suppressed_trigger_inputs.get(key, 0) + 1
            return None
    def _consume_suppressed_trigger_input(self = None, trigger_type = None, trigger_value = None):
        key = f'''{trigger_type}:{trigger_value}'''
        with self._trigger_lock:
            count = int(self._suppressed_trigger_inputs.get(key, 0))
            if count <= 0:
                return False
            if count == 1:
                self._suppressed_trigger_inputs.pop(key, None)
            else:
                self._suppressed_trigger_inputs[key] = count - 1
            return True

    def _begin_input_block(self):
        with self._input_block_lock:
            was_blocked = self._input_block_count > 0
            self._input_block_count += 1
        if not was_blocked:
            with self._trigger_lock:
                self._pressed_trigger_keys.clear()
                self._pressed_trigger_mouse_inputs.clear()
                self._suppressed_trigger_inputs.clear()
            self._pressed_pause_inputs.clear()
            self._apply_hold_stop()
            return None
        return None

    
    def _end_input_block(self):
        with self._input_block_lock:
            if self._input_block_count <= 0:
                return None
            self._input_block_count -= 1
            still_blocked = self._input_block_count > 0
        if not still_blocked:
            if self.running:
                if not self.paused_hold:
                    if not self.loot_hold_active:
                        for a in self.actions:
                            if not a.get('mode') == 'hold':
                                continue
                            self._apply_hold_start(a)
                        return None
                    return None
                return None
            return None
        return None

    
    def _is_input_blocked(self = None):
        with self._input_block_lock:
            return self._input_block_count > 0
    def _first_hotkey(self = None, values = None, default = None):
        for value in values:
            value = str(value or '').strip()
            if not value:
                continue
            
            return value
        return default

    
    def _normalize_hotkey_list(self, data = None, list_key = None, single_key = None, default = ''):
        raw_values = None
        if isinstance(data, dict):
            raw_values = data.get(list_key)
            if not isinstance(raw_values, list):
                single_value = data.get(single_key)
                raw_values = [
                    single_value] if isinstance(single_value, str) and single_value.strip() else []
        else:
            raw_values = []
        clean = []
        seen = set()
        for value in raw_values:
            value = str(value or '').strip()
            if not value or value in seen:
                continue
            clean.append(value)
            seen.add(value)
        if clean:
            return clean
        return [
            default]

    
    def _sync_legacy_hotkey_values(self):
        self.start_keys = self._normalize_hotkey_list({
            'start_keys': self.start_keys }, 'start_keys', 'start_key', 'Key.f1')
        self.stop_keys = self._normalize_hotkey_list({
            'stop_keys': self.stop_keys }, 'stop_keys', 'stop_key', 'Key.f2')
        if self.start_stop_same_key:
            self.stop_keys = list(self.start_keys)
        self.start_key_str = self._first_hotkey(self.start_keys, 'Key.f1')
        self.stop_key_str = self._first_hotkey(self.stop_keys, 'Key.f2')
        self.pause_hold_keys = self._pause_key_values()

    
    def _hotkey_list_summary(self = None, values = None):
        clean = [hotkey_display_text(x) for x in values if str(x if x else '').strip()]
        if not clean:
            return '없음'
        if len(clean) <= 2:
            return ' / '.join(clean)
        return f'''{clean[0]} / {clean[1]} 외 {len(clean) - 2}개'''
        

    
    def _refresh_start_key_var(self):
        self._sync_legacy_hotkey_values()
        if hasattr(self, 'start_key_var'):
            self.start_key_var.set(self._hotkey_list_summary(self.start_keys))
            return None

    
    def _refresh_stop_key_var(self):
        self._sync_legacy_hotkey_values()
        if hasattr(self, 'stop_key_var'):
            self.stop_key_var.set(self._hotkey_list_summary(self.stop_keys))
            return None

    
    def _find_hotkey_in_list(self = None, hotkeys = None, input_type = None, input_value = None):
        for hotkey in hotkeys:
            if not self._hotkey_matches(hotkey, input_type, input_value):
                continue
            
            return hotkey
        return ''

    
    def _find_start_hotkey(self = None, input_type = None, input_value = None):
        return self._find_hotkey_in_list(self.start_keys, input_type, input_value)

    
    def _find_stop_hotkey(self = None, input_type = None, input_value = None):
        return self._find_hotkey_in_list(self.stop_keys, input_type, input_value)

    
    def _pause_key_values(self = None):
        values = []
        for item in getattr(self, 'pause_key_items', []) or []:
            if isinstance(item, dict):
                key = str(item.get('key', '') or '').strip()
            else:
                key = str(item or '').strip()
            if not key:
                continue
            if key in values:
                continue
            values.append(key)
        return values

    
    def _pause_key_mode_label(self = None, mode = None):
        if mode == 'toggle':
            return '토글'
        return '홀드'

    
    def _has_active_pause(self = None):
        return bool(self._pressed_pause_inputs or self._toggle_pause_active_key)

    
    def _find_pause_item(self = None, input_type = None, input_value = None):
        for item in self.pause_key_items:
            key = str(item.get('key', '') or '').strip()
            if not key:
                continue
            if not self._hotkey_matches(key, input_type, input_value):
                continue
            mode = item.get('mode', 'hold')

            return {
                'key': key,
                'mode': 'toggle' if mode == 'toggle' else 'hold' }

    
    def _toggle_pause_by_key(self = None, pause_key = None):
        pause_key = str(pause_key or '').strip()
        if not pause_key:
            return None
        if not self.running and not self.triggers_enabled:
            self._toggle_pause_active_key = ''
            return None
        if self._toggle_pause_active_key == pause_key:
            self._toggle_pause_active_key = ''
            if not self._pressed_pause_inputs:
                self._stop_pause_hold()
            return None
        if self.paused_hold:
            return None
        self._toggle_pause_active_key = pause_key
        self._start_pause_hold()

    
    def _hotkey_matches(self = None, hotkey_value = None, input_type = None, input_value = None):
        if input_type == 'key':
            return not is_mouse_hotkey(hotkey_value) and hotkey_value == input_value
        if input_type == 'mouse':
            return is_mouse_hotkey(hotkey_value) and hotkey_value == input_value
        return False

    
    def _pause_keys_summary(self = None):
        values = self._pause_key_values()
        if not values:
            return '없음'
        displays = [hotkey_display_text(x) for x in values]
        if len(displays) <= 2:
            return ' / '.join(displays)
        return f'''{displays[0]} / {displays[1]} 외 {len(displays) - 2}개'''
        

    
    def _refresh_pause_key_var(self):
        self.pause_hold_keys = self._pause_key_values()
        if hasattr(self, 'pause_key_var'):
            self.pause_key_var.set(self._pause_keys_summary())
            return None

    
    def _reserved_hotkeys(self = None, include_pause = None):
        reserved = set(self.start_keys)
        reserved.update(self.stop_keys)
        reserved.update({
            self.loot_hold_key_str,
            self.quick_right_hold_key_str})
        if include_pause:
            reserved.update(self._pause_key_values())
        return {x for x in reserved if x}
        

    
    def _normalize_pause_keys(self = None, data = None):
        items = []
        if isinstance(data, dict):
            raw_items = data.get('pause_key_items')
            if raw_items is None:
                raw_items = data.get('pause_keys')
            if raw_items is None and isinstance(data.get('pause_key'), str):
                raw_items = [
                    data.get('pause_key')]
        else:
            raw_items = getattr(self, 'pause_key_items', []) or getattr(self, 'pause_hold_keys', []) or []
        if isinstance(raw_items, list):
            for raw in raw_items:
                if isinstance(raw, dict):
                    key = str(raw.get('key', '') or '').strip()
                    mode = 'toggle' if raw.get('mode') == 'toggle' else 'hold'
                else:
                    key = str(raw or '').strip()
                    mode = 'hold'
                if not key:
                    continue
                items.append({
                    'key': key,
                    'mode': mode })
        clean = []
        seen = set()
        for item in items:
            key = item['key']
            if key in seen:
                continue
            clean.append({
                'key': key,
                'mode': item['mode'] })
            seen.add(key)
        if clean:
            return clean
        return [
            {
                'key': '`',
                'mode': 'hold' }]

    
    def _normalize_mouse_dict(self = None, item = None, key_prefix = None):
        if not isinstance(item, dict):
            return item
        button_key = f'''{key_prefix}button''' if key_prefix else 'button'
        type_key = f'''{key_prefix}button_type''' if key_prefix else 'button_type'
        if button_key not in item:
            return item
        button = str(item.get(button_key, '') or '')
        button_type = normalize_mouse_button_type(item.get(type_key), button)
        item[type_key] = button_type
        item[button_key] = button
        return item

    
    def _normalize_loaded_actions(self):
        for action in self.actions:
            if not isinstance(action, dict):
                continue
            if not action.get('type') == 'mouse':
                continue
            self._normalize_mouse_dict(action)
        for action in self.trigger_actions:
            if not isinstance(action, dict):
                continue
            if action.get('trigger_type') == 'mouse':
                self._normalize_mouse_dict(action, 'trigger_')
            steps = action.get('steps')
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if not step.get('target_type') == 'mouse':
                    continue
                self._normalize_mouse_dict(step, 'target_')

    
    def _action_mouse_storage(self = None, action = None):
        button = str(action.get('button', 'left') or 'left')
        button_type = normalize_mouse_button_type(action.get('button_type'), button)
        return (button_type, button)

    
    def _trigger_action_mouse_storage(self = None, action = None):
        button = str(action.get('trigger_button', 'left') or 'left')
        button_type = normalize_mouse_button_type(action.get('trigger_button_type'), button)
        return (button_type, button)

    
    def _trigger_step_mouse_storage(self = None, step = None):
        button = str(step.get('target_button', 'left') or 'left')
        button_type = normalize_mouse_button_type(step.get('target_button_type'), button)
        return (button_type, button)

    
    def _trigger_action_input_value(self = None, action = None):
        if action.get('trigger_type', 'key') == 'key':
            return str(action.get('trigger_key', '') or '')
        (button_type, button) = self._trigger_action_mouse_storage(action)
        return mouse_button_hotkey(button, button_type)

    
    def _trigger_step_input_value(self = None, step = None):
        if step.get('target_type', 'key') == 'key':
            return str(step.get('target_key', '') or '')
        (button_type, button) = self._trigger_step_mouse_storage(step)
        return mouse_button_hotkey(button, button_type)

    
    def _is_trigger_input_pressed(self = None, trigger_type = None, trigger_value = None):
        with self._trigger_lock:
            if trigger_type == 'key':
                return trigger_value in self._pressed_trigger_keys
            if trigger_type == 'mouse':
                return trigger_value in self._pressed_trigger_mouse_inputs
            return False

    
    def _same_trigger_and_step(self = None, action = None, step = None):
        if action.get('trigger_type') != step.get('target_type'):
            return False
        return self._trigger_action_input_value(action) == self._trigger_step_input_value(step)

    
    def _handle_start_hotkey_press(self):
        if self.paused_hold:
            if self._toggle_pause_active_key:
                self._toggle_pause_active_key = ''
                if self._pressed_pause_inputs:
                    self.status_var.set('일시정지중 (홀드 일시정지키를 떼면 재개됩니다)')
                    return None
                self._stop_pause_hold()
                self._enforce_active_program_guard()
                return None
            if self._pressed_pause_inputs:
                self.status_var.set('일시정지중 (홀드 일시정지키를 떼면 재개됩니다)')
                return None
        if self.start_stop_same_key:
            if self.running or self.triggers_enabled or self.loot_hold_active:
                self._stop_macro()
                return None
            if not self._is_active_program_allowed():
                self._apply_hold_stop()
                self.status_var.set('동작시킬 프로그램이 현재 활성창이 아닙니다. 선택한 프로그램 창에서 시작하세요.')
                return None
            self._start_macro()
            return None
        if not self._is_active_program_allowed():
            self._apply_hold_stop()
            self.status_var.set('동작시킬 프로그램이 현재 활성창이 아닙니다. 선택한 프로그램 창에서 시작하세요.')
            return None
        self._start_macro()

    
    def _start_pause_hold(self):
        if self.running or self.triggers_enabled:
            if not self.paused_hold:
                self.paused_hold = True
                self._triggers_enabled_before_pause = self.triggers_enabled
                with self._trigger_lock:
                    self._pressed_trigger_keys.clear()
                    self._pressed_trigger_mouse_inputs.clear()
                    self._suppressed_trigger_inputs.clear()
                self._apply_hold_stop()
                self.status_var.set('일시정지중 (반복 키/자동 순차 실행 모두 중지, 일시정지키를 모두 떼면 재개)')
                return None
            return None
        return None

    
    def _stop_pause_hold(self):
        if not self.paused_hold:
            return None
        if self._has_active_pause():
            return None
        self.paused_hold = False
        self.triggers_enabled = self._triggers_enabled_before_pause
        self._triggers_enabled_before_pause = False
        if self.running and not self.loot_hold_active:
            for a in self.actions:
                if not a.get('mode') == 'hold':
                    continue
                self._apply_hold_start(a)
        if self.loot_hold_active:
            self.status_var.set('루팅중 (기존 매크로 임시정지, 루팅키를 떼면 재개)')
            return None
        if self.running and self.triggers_enabled:
            self.status_var.set('실행중 (반복 키/자동 순차 실행 활성화, 종료키로 모두 중지)')
            return None
        if self.running:
            self.status_var.set('실행중 (반복 키만 활성화, 종료키로 중지)')
            return None
        if self.triggers_enabled:
            self.status_var.set('자동 순차 실행 활성화중 (종료키로 중지)')
            return None
        self.status_var.set('대기중 (시작키를 누르면 반복 키/자동 순차 실행 시작, 종료키로 모두 중지)')

    
    def _start_global_listener(self):
        
        def should_ignore_trigger():
            return False

        
        def on_press(k = None):
            ks = key_to_str(k)
            if not ks:
                return None
            if self._is_input_blocked():
                return None
            if self._find_start_hotkey('key', ks):
                self._handle_start_hotkey_press()
                return None
            if not self.start_stop_same_key and self._find_stop_hotkey('key', ks):
                self._stop_macro()
                return None
            pause_item = self._find_pause_item('key', ks)
            if pause_item:
                if pause_item['mode'] == 'toggle':
                    self._toggle_pause_by_key(pause_item['key'])
                    return None
                self._pressed_pause_inputs.add(pause_item['key'])
                self._start_pause_hold()
                return None
            if self._hotkey_matches(self.loot_hold_key_str, 'key', ks):
                self._start_loot_hold()
                return None
            if self._hotkey_matches(self.quick_right_hold_key_str, 'key', ks):
                self._start_quick_right_hold()
                return None
            if not self.triggers_enabled:
                return None
            if self.paused_hold or self.loot_hold_active:
                return None
            if should_ignore_trigger():
                return None
            if self._consume_suppressed_trigger_input('key', ks):
                return None
            if ks not in self._pressed_trigger_keys:
                self._pressed_trigger_keys.add(ks)
                self._fire_trigger('key', ks)
                return None

        
        def on_release(k = None):
            ks = key_to_str(k)
            if not ks:
                return None
            self._pressed_trigger_keys.discard(ks)
            if self._is_input_blocked():
                return None
            pause_item = self._find_pause_item('key', ks)
            if pause_item and pause_item['mode'] == 'hold':
                self._pressed_pause_inputs.discard(pause_item['key'])
                if not self._pressed_pause_inputs:
                    self._stop_pause_hold()
                return None
            if self._hotkey_matches(self.loot_hold_key_str, 'key', ks):
                self._stop_loot_hold()
                return None
            if self._hotkey_matches(self.quick_right_hold_key_str, 'key', ks):
                self._stop_quick_right_hold()
                return None

        
        def on_click(x = None, y = None, button = None, pressed = None):
            mouse_input = mouse_hotkey_from_obj(button)
            if not mouse_input:
                return None
            if not pressed:
                self._pressed_trigger_mouse_inputs.discard(mouse_input)
                if self._is_input_blocked():
                    return None
                pause_item = self._find_pause_item('mouse', mouse_input)
                if pause_item and pause_item['mode'] == 'hold':
                    self._pressed_pause_inputs.discard(pause_item['key'])
                    if not self._pressed_pause_inputs:
                        self._stop_pause_hold()
                    return None
                if self._hotkey_matches(self.loot_hold_key_str, 'mouse', mouse_input):
                    self._stop_loot_hold()
                    return None
                if self._hotkey_matches(self.quick_right_hold_key_str, 'mouse', mouse_input):
                    self._stop_quick_right_hold()
                    return None
                return None
            if self._is_input_blocked():
                return None
            if self._find_start_hotkey('mouse', mouse_input):
                self._handle_start_hotkey_press()
                return None
            if not self.start_stop_same_key and self._find_stop_hotkey('mouse', mouse_input):
                self._stop_macro()
                return None
            pause_item = self._find_pause_item('mouse', mouse_input)
            if pause_item:
                if pause_item['mode'] == 'toggle':
                    self._toggle_pause_by_key(pause_item['key'])
                    return None
                self._pressed_pause_inputs.add(pause_item['key'])
                self._start_pause_hold()
                return None
            if self._hotkey_matches(self.loot_hold_key_str, 'mouse', mouse_input):
                self._start_loot_hold()
                return None
            if self._hotkey_matches(self.quick_right_hold_key_str, 'mouse', mouse_input):
                self._start_quick_right_hold()
                return None
            if not self.triggers_enabled:
                return None
            if self.paused_hold or self.loot_hold_active:
                return None
            if should_ignore_trigger():
                return None
            if self._consume_suppressed_trigger_input('mouse', mouse_input):
                return None
            if mouse_input not in self._pressed_trigger_mouse_inputs:
                self._pressed_trigger_mouse_inputs.add(mouse_input)
                self._fire_trigger('mouse', mouse_input)
                return None

        self._kb_listener = keyboard.Listener(on_press = on_press, on_release = on_release)
        self._kb_listener.daemon = True
        self._kb_listener.start()
        self._mouse_listener = mouse.Listener(on_click = on_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()
        self._gamepad_on_press = on_press
        self._gamepad_on_release = on_release
        self._start_gamepad_listener()

    def _start_gamepad_listener(self):
        if not GAMEPAD_SUPPORTED:
            return None

        def gp_press(name = None):
            vp = self.virtual_pad
            if vp is not None and vp.is_active(name):
                return
            handler = getattr(self, '_gamepad_on_press', None)
            if handler is not None:
                handler(GamepadButton(name))

        def gp_release(name = None):
            vp = self.virtual_pad
            if vp is not None and vp.is_active(name):
                return
            handler = getattr(self, '_gamepad_on_release', None)
            if handler is not None:
                handler(GamepadButton(name))

        try:
            if getattr(self, '_gamepad_manager', None) is None:
                self._gamepad_manager = gamepad_input.GamepadManager()
            self._gamepad_manager.start(gp_press, gp_release)
        except Exception:
            self._gamepad_manager = None

    
    def _capture_one_key(self = None, title = None, on_done = None):
        self._begin_input_block()
        win = tk.Toplevel(self)
        win.title(title)
        self._center_child_window(win, 360, 140)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        listener_ref = {
            'listener': None }
        closed_ref = {
            'closed': False }
        info = ttk.Label(win, text = '설정할 키를 한 번 눌러주세요.')
        info.pack(pady = (22, 10))
        key_var = tk.StringVar(value = '')
        ttk.Entry(win, textvariable = key_var, width = 24, state = 'readonly', justify = 'center').pack()
        
        def close():
            if closed_ref['closed']:
                return None
            closed_ref['closed'] = True
            listener = listener_ref.get('listener')
            if listener is not None:
                
                try:
                    listener.stop()
                except Exception:
                    pass

                self._end_input_block()
                
                try:
                    win.grab_release()
                except Exception:
                    pass

                
                try:
                    win.destroy()
                    return None
                except Exception:
                    return None


        win.protocol('WM_DELETE_WINDOW', close)
        ttk.Button(win, text = '취소', command = close).pack(pady = 12)
        
        def on_press(k = None):
            if closed_ref['closed']:
                return False
            ks = key_to_str(k)
            if ks:
                key_var.set(ks)
                on_done(ks)
                close()
                return False

        listener = keyboard.Listener(on_press = on_press)
        listener.daemon = True
        listener_ref['listener'] = listener
        listener.start()
        if GAMEPAD_SUPPORTED:
            info.configure(text = '키 또는 게임패드 버튼을 한 번 눌러주세요.')
            mgr = getattr(self, '_gamepad_manager', None)
            if mgr is not None:
                mgr.clear_captured()

            def poll_gamepad():
                if closed_ref['closed']:
                    return None
                m = getattr(self, '_gamepad_manager', None)
                name = m.poll_captured() if m is not None else None
                if name:
                    key_var.set(hotkey_display_text(name))
                    on_done(name)
                    close()
                    return None
                win.after(40, poll_gamepad)

            win.after(40, poll_gamepad)


    def _capture_custom_mouse_button(self = None, title = None, on_done = None):
        self._begin_input_block()
        win = tk.Toplevel(self)
        win.title(title)
        self._center_child_window(win, 460, 230)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        listener_ref = {
            'listener': None }
        closed_ref = {
            'closed': False }
        detected_var = tk.StringVar(value = '')
        guide_var = tk.StringVar(value = '마우스 좌/우/휠클릭을 제외한 버튼을 누른 후 감지된 버튼만 등록가능')
        root = ttk.Frame(win, padding = 14)
        root.pack(fill = 'both', expand = True)
        ttk.Label(root, textvariable = guide_var, wraplength = 420).pack(anchor = 'w', pady = (0, 12))
        box = ttk.LabelFrame(root, text = '감지된 버튼', padding = 10)
        box.pack(fill = 'x')
        ttk.Entry(box, textvariable = detected_var, width = 34, state = 'readonly', justify = 'center').pack(fill = 'x')
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (16, 0))
        
        def close():
            if closed_ref['closed']:
                return None
            closed_ref['closed'] = True
            listener = listener_ref.get('listener')
            if listener is not None:
                
                try:
                    listener.stop()
                except Exception:
                    pass

                self._end_input_block()
                
                try:
                    win.grab_release()
                except Exception:
                    pass

                
                try:
                    win.destroy()
                    return None
                except Exception:
                    return None


        
        def submit():
            value = detected_var.get().strip()
            if not value:
                messagebox.showinfo('안내', '좌/우/휠클릭을 제외한 마우스 버튼을 먼저 눌러주세요.')
                return None
            on_done(mouse_button_hotkey(value, 'custom'))
            close()

        win.protocol('WM_DELETE_WINDOW', close)
        ttk.Button(btns, text = '취소', command = close).pack(side = 'right')
        ttk.Button(btns, text = '등록', command = submit).pack(side = 'right', padx = (0, 8))
        
        def on_click(x = None, y = None, button = None, pressed = None):
            if closed_ref['closed']:
                return False
            if not pressed:
                return None
            if is_basic_mouse_button_obj(button):
                guide_var.set('좌/우/휠클릭은 기본 버튼에서 선택하세요. 그외 버튼만 감지됩니다.')
                return None
            (button_type, button_value) = mouse_button_storage_from_obj(button)
            if button_type == 'custom':
                if button_value:
                    detected_var.set(button_value)
                    guide_var.set('감지되었습니다. 등록을 누르면 이 버튼이 저장됩니다.')
                    return None
                return None

        listener = mouse.Listener(on_click = on_click)
        listener.daemon = True
        listener_ref['listener'] = listener
        listener.start()

    
    def _capture_one_hotkey(self = None, title = None, on_done = None):
        self._begin_input_block()
        win = tk.Toplevel(self)
        win.title(title)
        self._center_child_window(win, 460, 280)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        listener_ref = {
            'listener': None }
        closed_ref = {
            'closed': False }
        root = ttk.Frame(win, padding = 12)
        root.pack(fill = 'both', expand = True)
        notebook = ttk.Notebook(root)
        notebook.pack(fill = 'both', expand = True)
        keyboard_tab = ttk.Frame(notebook, padding = 12)
        mouse_tab = ttk.Frame(notebook, padding = 12)
        notebook.add(keyboard_tab, text = '키보드')
        notebook.add(mouse_tab, text = '마우스')
        key_var = tk.StringVar(value = '')
        mouse_choice_var = tk.StringVar(value = 'left')
        custom_mouse_var = tk.StringVar(value = '')
        ttk.Label(keyboard_tab, text = '설정할 키보드 키를 한 번 눌러주세요.').pack(pady = (12, 10))
        ttk.Entry(keyboard_tab, textvariable = key_var, width = 28, state = 'readonly', justify = 'center').pack()
        ttk.Label(mouse_tab, text = '사용할 마우스 버튼을 선택하세요.').pack(anchor = 'w', pady = (4, 8))
        
        def select_basic_mouse():
            custom_mouse_var.set('')

        ttk.Radiobutton(mouse_tab, text = '왼쪽버튼', value = 'left', variable = mouse_choice_var, command = select_basic_mouse).pack(anchor = 'w', pady = 2)
        ttk.Radiobutton(mouse_tab, text = '오른쪽버튼', value = 'right', variable = mouse_choice_var, command = select_basic_mouse).pack(anchor = 'w', pady = 2)
        ttk.Radiobutton(mouse_tab, text = '휠클릭', value = 'middle', variable = mouse_choice_var, command = select_basic_mouse).pack(anchor = 'w', pady = 2)
        custom_row = ttk.Frame(mouse_tab)
        custom_row.pack(fill = 'x', pady = 2)
        ttk.Radiobutton(custom_row, text = '그외 버튼', value = 'custom', variable = mouse_choice_var).pack(side = 'left')
        ttk.Entry(custom_row, textvariable = custom_mouse_var, width = 24, state = 'readonly', justify = 'center').pack(side = 'left', fill = 'x', expand = True, padx = (8, 8))
        
        def pick_custom_mouse():
            
            def done(value = None):
                custom_mouse_var.set(value)
                mouse_choice_var.set('custom')

            self._capture_custom_mouse_button('그외 마우스 버튼추가', done)

        ttk.Button(custom_row, text = '그외 버튼추가', command = pick_custom_mouse).pack(side = 'left')
        
        def close():
            if closed_ref['closed']:
                return None
            closed_ref['closed'] = True
            listener = listener_ref.get('listener')
            if listener is not None:
                
                try:
                    listener.stop()
                except Exception:
                    pass

                self._end_input_block()
                
                try:
                    win.grab_release()
                except Exception:
                    pass

                
                try:
                    win.destroy()
                    return None
                except Exception:
                    return None


        win.protocol('WM_DELETE_WINDOW', close)
        
        def choose_mouse():
            if closed_ref['closed']:
                return None
            choice = mouse_choice_var.get()
            if choice == 'custom':
                custom_value = custom_mouse_var.get().strip()
                if not custom_value:
                    messagebox.showinfo('안내', '그외 버튼추가를 눌러 마우스 버튼을 먼저 등록하세요.')
                    return None
                on_done(custom_value)
                close()
                return None
            hk = mouse_button_hotkey(choice, 'basic')
            if hk:
                on_done(hk)
                close()
                return None

        bottom = ttk.Frame(root)
        bottom.pack(fill = 'x', pady = (10, 0))
        ttk.Button(bottom, text = '취소', command = close).pack(side = 'right')
        ttk.Button(bottom, text = '확인', command = choose_mouse).pack(side = 'right', padx = (0, 8))
        
        def on_press(k = None):
            if closed_ref['closed']:
                return False
            ks = key_to_str(k)
            if ks:
                key_var.set(ks)
                on_done(ks)
                close()
                return False

        listener = keyboard.Listener(on_press = on_press)
        listener.daemon = True
        listener_ref['listener'] = listener
        listener.start()
        if GAMEPAD_SUPPORTED:
            gamepad_tab = ttk.Frame(notebook, padding = 12)
            notebook.add(gamepad_tab, text = '게임패드')
            gp_var = tk.StringVar(value = '')
            ttk.Label(gamepad_tab, text = '설정할 게임패드 버튼을 한 번 눌러주세요.\n(Xbox / PlayStation / 레노버 리전 고2 등 지원)').pack(pady = (12, 10))
            ttk.Entry(gamepad_tab, textvariable = gp_var, width = 28, state = 'readonly', justify = 'center').pack()
            mgr = getattr(self, '_gamepad_manager', None)
            if mgr is not None:
                mgr.clear_captured()

            def poll_gamepad():
                if closed_ref['closed']:
                    return None
                m = getattr(self, '_gamepad_manager', None)
                name = m.poll_captured() if m is not None else None
                if name:
                    gp_var.set(hotkey_display_text(name))
                    on_done(name)
                    close()
                    return None
                win.after(40, poll_gamepad)

            win.after(40, poll_gamepad)


    def _pick_safe_default_stop_key(self = None):
        candidates = [
            'Key.f2',
            'Key.f4',
            'Key.f5',
            'Key.f6',
            'Key.f7',
            'Key.f8']
        blocked = set(self.start_keys)
        blocked.update({
            self.loot_hold_key_str,
            self.quick_right_hold_key_str})
        blocked.update(self._pause_key_values())
        for candidate in candidates:
            if candidate in blocked:
                continue
            return candidate
        return 'Key.f2'

    
    def _pick_safe_default_loot_key(self = None, extra_blocked = None):
        candidates = [
            'Key.f3',
            'Key.f5',
            'Key.f6',
            'Key.f7',
            'Key.f8',
            'Key.f9',
            'Key.f10',
            'Key.f11',
            'Key.f12']
        blocked = set(extra_blocked or [])
        blocked.update(self.start_keys)
        blocked.update(self.stop_keys)
        blocked.update({
            self.quick_right_hold_key_str})
        blocked.update(self._pause_key_values())
        for candidate in candidates:
            if candidate in blocked:
                continue
            return candidate
        return 'Key.f3'

    
    def _pick_safe_default_quick_right_key(self = None, extra_blocked = None):
        candidates = [
            'Key.f4',
            'Key.f5',
            'Key.f6',
            'Key.f7',
            'Key.f8',
            'Key.f9',
            'Key.f10',
            'Key.f11',
            'Key.f12']
        blocked = set(extra_blocked or [])
        blocked.update(self.start_keys)
        blocked.update(self.stop_keys)
        blocked.update({
            self.loot_hold_key_str})
        blocked.update(self._pause_key_values())
        for candidate in candidates:
            if candidate in blocked:
                continue
            return candidate
        return 'Key.f4'

    
    def _sync_start_stop_same_key_ui(self):
        if self.start_stop_same_key:
            self.stop_keys = list(self.start_keys)
            self._refresh_stop_key_var()
            if hasattr(self, 'stop_key_entry'):
                self.stop_key_entry.configure(state = 'disabled')
            if hasattr(self, 'stop_key_button'):
                self.stop_key_button.configure(state = 'disabled')
                return None
            return None
        overlap = bool(set(self.stop_keys) & set(self.start_keys))
        if overlap:
            restored = list(getattr(self, '_stop_keys_before_same_toggle', []) or [])
            blocked = set(self.start_keys)
            blocked.update({
                self.loot_hold_key_str,
                self.quick_right_hold_key_str})
            blocked.update(self._pause_key_values())
            restored = [x for x in restored if x and x not in blocked]
            self.stop_keys = restored if restored else [
                self._pick_safe_default_stop_key()]
            self._refresh_stop_key_var()
        if hasattr(self, 'stop_key_entry'):
            self.stop_key_entry.configure(state = 'readonly')
        if hasattr(self, 'stop_key_button'):
            self.stop_key_button.configure(state = 'normal')
            return None
        return None
        

    
    def _toggle_start_stop_same_key(self):
        next_value = bool(self.start_stop_same_var.get())
        if next_value:
            self._stop_keys_before_same_toggle = list(self.stop_keys)
            self.start_stop_same_key = True
        else:
            self.start_stop_same_key = False
        self._sync_start_stop_same_key_ui()

    
    def _set_start_key(self):
        HotkeyListDialog(self, title = '시작키 설정', kind = 'start')

    
    def _set_stop_key(self):
        if self.start_stop_same_key:
            messagebox.showinfo('안내', '시작/종료키 동일키 사용 중에는 종료키를 따로 설정할 수 없습니다.')
            return None
        HotkeyListDialog(self, title = '종료키 설정', kind = 'stop')

    
    def _set_pause_key(self):
        PauseKeysDialog(self)

    
    def _set_loot_key(self):
        
        def done(ks = None):
            if ks in self.start_keys or ks in self.stop_keys or ks in self._pause_key_values() or ks == self.quick_right_hold_key_str:
                messagebox.showwarning('경고', '빨리줍기키는 시작키/종료키/일시정지키/빠른우클릭키와 다르게 설정하세요.')
                return None
            self.loot_hold_key_str = ks
            self.loot_key_var.set(hotkey_display_text(ks))

        self._capture_one_hotkey('빨리줍기키 설정(홀드)', done)

    
    def _set_quick_right_key(self):
        
        def done(ks = None):
            if ks in self.start_keys or ks in self.stop_keys or ks in self._pause_key_values() or ks == self.loot_hold_key_str:
                messagebox.showwarning('경고', '빠른우클릭키는 시작키/종료키/일시정지키/빨리줍기키와 다르게 설정하세요.')
                return None
            self.quick_right_hold_key_str = ks
            self.quick_right_key_var.set(hotkey_display_text(ks))

        self._capture_one_hotkey('빠른우클릭키 설정(홀드)', done)

    
    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for a in self.actions:
            kind = '키' if a['type'] == 'key' else '마우스'
            if a['type'] == 'key':
                target = a.get('key', '')
            else:
                (button_type, button) = self._action_mouse_storage(a)
                target = mouse_button_display_text(button_type, button)
            mode = '클릭' if a.get('mode') == 'click' else '누르기'
            interval = '' if a.get('mode') == 'hold' else format_interval_value(a.get('interval', 0.0001))
            self.tree.insert('', 'end', iid = a['id'], values = (kind, target, mode, interval))

    
    def _trigger_steps(self = None, a = None):
        steps = a.get('steps')
        if isinstance(steps, list) and steps:
            clean_steps = []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                clean_step = dict(step)
                clean_step.setdefault('id', uuid.uuid4().hex)
                clean_step.setdefault('delay', 0.1)
                clean_step.setdefault('target_type', 'key')
                clean_step.setdefault('target_key', '')
                clean_step.setdefault('target_button', 'left')
                if clean_step.get('target_type') == 'mouse':
                    self._normalize_mouse_dict(clean_step, 'target_')
                clean_steps.append(clean_step)
            return clean_steps
        target_type = a.get('target_type', 'key')
        step = {
            'id': uuid.uuid4().hex,
            'delay': a.get('delay', 0.1),
            'target_type': target_type,
            'target_key': a.get('target_key', '') if target_type == 'key' else '',
            'target_button_type': normalize_mouse_button_type(a.get('target_button_type'), a.get('target_button', 'left')),
            'target_button': a.get('target_button', 'left') if target_type == 'mouse' else 'left' }
        return [
            step]

    
    def _format_trigger_target(self = None, step = None):
        target_type = step.get('target_type', 'key')
        if target_type == 'key':
            return f'''키 {step.get('target_key', '')}'''
        (button_type, button) = self._trigger_step_mouse_storage(step)
        return f'''마우스 {mouse_button_display_text(button_type, button)}'''

    
    def _refresh_trigger_tree(self):
        for i in self.trigger_tree.get_children():
            self.trigger_tree.delete(i)
        for a in self.trigger_actions:
            trigger_type = a.get('trigger_type', 'key')
            if trigger_type == 'key':
                trigger_text = f'''키: {a.get('trigger_key', '')}'''
            else:
                (button_type, button) = self._trigger_action_mouse_storage(a)
                trigger_text = f'''마우스: {mouse_button_display_text(button_type, button)}'''
            steps = self._trigger_steps(a)
            step_texts = []
            for step in sorted(steps, key = (lambda x: float(x.get('delay', 0.0001)))):
                try:
                    delay = parse_interval(str(step.get('delay', 0.0001)))
                except Exception:
                    delay = 0.0001
                step_texts.append(f'''{format_interval_value(delay)}초: {self._format_trigger_target(step)}''')
            count_text = f'''{len(steps)}개'''
            target_text = ' / '.join(step_texts)
            self.trigger_tree.insert('', 'end', iid = a['id'], values = (trigger_text, count_text, target_text))
        return None

    
    def _add_key_action(self):
        ActionDialog(self, mode = 'add', action_type = 'key', initial = None, on_submit = self._upsert_action)

    
    def _add_mouse_action(self):
        ActionDialog(self, mode = 'add', action_type = 'mouse', initial = None, on_submit = self._upsert_action)

    
    def _add_trigger_action(self):
        TriggerDialog(self, mode = 'add', initial = None, on_submit = self._upsert_trigger_action)

    
    def _get_selected_id(self):
        sel = self.tree.selection()
        if sel:
            return sel[0]

    
    def _get_selected_trigger_id(self):
        sel = self.trigger_tree.selection()
        if sel:
            return sel[0]

    
    def _edit_selected(self):
        sid = self._get_selected_id()
        if not sid:
            messagebox.showinfo('안내', '편집할 항목을 선택하세요.')
            return None
        a = next((x for x in self.actions if x['id'] == sid), None)
        if not a:
            return None
        ActionDialog(self, mode = 'edit', action_type = a['type'], initial = a, on_submit = self._upsert_action)

    
    def _edit_trigger_selected(self):
        sid = self._get_selected_trigger_id()
        if not sid:
            messagebox.showinfo('안내', '편집할 자동 순차 실행 항목을 선택하세요.')
            return None
        a = next((x for x in self.trigger_actions if x['id'] == sid), None)
        if not a:
            return None
        TriggerDialog(self, mode = 'edit', initial = a, on_submit = self._upsert_trigger_action)

    
    def _delete_selected(self):
        sid = self._get_selected_id()
        if not sid:
            messagebox.showinfo('안내', '삭제할 항목을 선택하세요.')
            return None
        self.actions = [a for a in self.actions if a['id'] != sid]
        self._refresh_tree()
        return None
        

    
    def _delete_trigger_selected(self):
        sid = self._get_selected_trigger_id()
        if not sid:
            messagebox.showinfo('안내', '삭제할 자동 순차 실행 항목을 선택하세요.')
            return None
        self.trigger_actions = [a for a in self.trigger_actions if a['id'] != sid]
        self._refresh_trigger_tree()
        return None
        

    
    def _upsert_action(self = None, action = None):
        existing = next((i for i, x in enumerate(self.actions) if x['id'] == action['id']), None)
        if existing is None:
            self.actions.append(action)
        else:
            self.actions[existing] = action
        self._refresh_tree()

    
    def _upsert_trigger_action(self = None, action = None):
        existing = next((i for i, x in enumerate(self.trigger_actions) if x['id'] == action['id']), None)
        if existing is None:
            self.trigger_actions.append(action)
        else:
            self.trigger_actions[existing] = action
        self._refresh_trigger_tree()

    
    def _settings_payload(self = None):
        self._sync_legacy_hotkey_values()
        return {
            'start_key': self.start_key_str,
            'stop_key': self.stop_key_str,
            'start_keys': list(self.start_keys),
            'stop_keys': list(self.stop_keys),
            'pause_keys': self._pause_key_values(),
            'pause_key_items': self._normalize_pause_keys(),
            'loot_key': self.loot_hold_key_str,
            'quick_right_key': self.quick_right_hold_key_str,
            'start_stop_same_key': bool(self.start_stop_same_key),
            'center_status_enabled': bool(self.center_status_enabled),
            'center_status_targets': self._normalize_center_status_targets(),
            'center_status_shape': self.center_status_shape if self.center_status_shape in frozenset({'bar', 'circle'}) else 'circle',
            'center_status_show_text': bool(self.center_status_show_text),
            'center_status_size_percent': self._center_status_size_percent_value(),
            'active_program_all': bool(self.active_program_all),
            'active_program_targets': self._normalize_active_program_targets(self.active_program_targets),
            'actions': self.actions,
            'trigger_actions': self.trigger_actions }

    
    def _apply_loaded_settings_data(self = None, data = None, show_warnings = None):
        start_keys = self._normalize_hotkey_list(data, 'start_keys', 'start_key', 'Key.f1')
        stop_keys = self._normalize_hotkey_list(data, 'stop_keys', 'stop_key', 'Key.f2')
        pause_key_items = self._normalize_pause_keys(data)
        pause_values = [item['key'] for item in pause_key_items]
        lk = data.get('loot_key', self.loot_hold_key_str)
        rk = data.get('quick_right_key', self.quick_right_hold_key_str)
        same_key = bool(data.get('start_stop_same_key', False))
        center_status_enabled = bool(data.get('center_status_enabled', self.center_status_enabled))
        center_status_targets = self._normalize_center_status_targets(data.get('center_status_targets', [
            'window']))
        center_status_shape = data.get('center_status_shape', 'circle')
        center_status_shape = center_status_shape if center_status_shape in frozenset({'bar', 'circle'}) else 'circle'
        center_status_show_text = bool(data.get('center_status_show_text', False))
        
        try:
            center_status_size_percent = int(data.get('center_status_size_percent', 100))
        except Exception:
            center_status_size_percent = 100
        center_status_size_percent = max(50, min(200, center_status_size_percent))
        active_program_targets = self._normalize_active_program_targets(data.get('active_program_targets', []))
        active_program_all = bool(data.get('active_program_all', True)) or not active_program_targets
        
        def warn(msg = None):
            if show_warnings:
                messagebox.showwarning('경고', msg)
                return None

        
        def pick_safe_stop_for_loaded():
            candidates = [
                'Key.f2',
                'Key.f4',
                'Key.f5',
                'Key.f6',
                'Key.f7',
                'Key.f8']
            blocked = set(start_keys)
            blocked.update(pause_values)
            blocked.update({
                lk,
                rk})
            for candidate in candidates:
                if candidate in blocked:
                    continue
                return candidate
            return 'Key.f2'

        if same_key:
            stop_keys = list(start_keys)
        else:
            overlap = set(start_keys) & set(stop_keys)
            if overlap:
                warn('불러온 설정에서 시작키/종료키가 겹칩니다. 겹친 종료키는 제외합니다.')
                stop_keys = [x for x in stop_keys if x not in overlap]
                if not stop_keys:
                    stop_keys = [
                        pick_safe_stop_for_loaded()]
        start_conflicts = set(start_keys) & set(pause_values)
        if start_conflicts:
            warn('불러온 설정에서 시작키가 일시정지키와 겹칩니다. 겹친 시작키는 제외합니다.')
            start_keys = [x for x in start_keys if x not in start_conflicts]
            if not start_keys:
                start_keys = [
                    'Key.f1']
        stop_conflicts = set(stop_keys) & set(pause_values)
        if stop_conflicts and not same_key:
            warn('불러온 설정에서 종료키가 일시정지키와 겹칩니다. 겹친 종료키는 제외합니다.')
            stop_keys = [x for x in stop_keys if x not in stop_conflicts]
            if not stop_keys:
                stop_keys = [
                    pick_safe_stop_for_loaded()]
        blocked_for_loot = set(start_keys)
        blocked_for_loot.update(stop_keys)
        blocked_for_loot.update(pause_values)
        blocked_for_loot.add(rk)
        if lk or lk in blocked_for_loot:
            warn('불러온 설정에서 빨리줍기키가 시작/종료/일시정지/빠른우클릭키와 동일합니다. 빨리줍기키는 안전한 기본값으로 변경합니다.')
            lk = self._pick_safe_default_loot_key(blocked_for_loot)
        blocked_for_quick_right = set(start_keys)
        blocked_for_quick_right.update(stop_keys)
        blocked_for_quick_right.update(pause_values)
        blocked_for_quick_right.add(lk)
        if rk or rk in blocked_for_quick_right:
            warn('불러온 설정에서 빠른우클릭키가 시작/종료/일시정지/빨리줍기키와 동일합니다. 빠른우클릭키는 안전한 기본값으로 변경합니다.')
            rk = self._pick_safe_default_quick_right_key(blocked_for_quick_right)
        self.start_keys = start_keys
        self.stop_keys = list(start_keys) if same_key else stop_keys
        self.pause_key_items = pause_key_items
        self.pause_hold_keys = self._pause_key_values()
        self.start_stop_same_key = same_key
        self.center_status_enabled = center_status_enabled
        self.center_status_targets = center_status_targets
        self.center_status_shape = center_status_shape
        self.center_status_show_text = center_status_show_text
        self.center_status_size_percent = center_status_size_percent
        self.active_program_all = active_program_all
        self.active_program_targets = active_program_targets
        self._active_program_blocked = False
        self.loot_hold_key_str = lk
        self.quick_right_hold_key_str = rk
        self._stop_keys_before_same_toggle = list(stop_keys if not same_key else [
            pick_safe_stop_for_loaded()])
        self._sync_legacy_hotkey_values()
        self.actions = data.get('actions', [])
        self.trigger_actions = data.get('trigger_actions', [])
        self._normalize_loaded_actions()
        return None
        
        
        
        

    
    def _load_last_settings_silent(self):
        path = getattr(self, '_last_settings_path', '')
        if not path or not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r', encoding = 'utf-8') as f:
                data = json.load(f)
            self._apply_loaded_settings_data(data, show_warnings = False)
            return None
        except Exception:
            return None


    
    def _save_last_settings_silent(self):
        path = getattr(self, '_last_settings_path', '')
        if not path:
            return None
        
        try:
            with open(path, 'w', encoding = 'utf-8') as f:
                json.dump(self._settings_payload(), f, ensure_ascii = False, indent = 2)
            return None
        except Exception:
            return None

    
    def _on_close(self):

        try:
            self._stop_macro()
        except Exception:
            pass
        try:
            mgr = getattr(self, '_gamepad_manager', None)
            if mgr is not None:
                mgr.stop()
        except Exception:
            pass
        try:
            if self._status_refresh_after_id is not None:
                self.after_cancel(self._status_refresh_after_id)
                self._status_refresh_after_id = None
        except Exception:
            pass
        try:
            if self._center_overlay_reposition_after_id is not None:
                self.after_cancel(self._center_overlay_reposition_after_id)
                self._center_overlay_reposition_after_id = None
        except Exception:
            pass
        try:
            if self._center_overlay_click_through_retry_after_id is not None:
                self.after_cancel(self._center_overlay_click_through_retry_after_id)
                self._center_overlay_click_through_retry_after_id = None
        except Exception:
            pass
        self._save_last_settings_silent()
        try:
            self._destroy_center_status_overlays()
        except Exception:
            pass
        try:
            self.destroy()
            return None
        except Exception:
            return None

    
    def _save(self):
        if self.running or self.triggers_enabled or self.paused_hold or self.loot_hold_active:
            messagebox.showwarning('안내', '실행 중이거나 일시정지/빠른클릭 중에는 저장할 수 없습니다. 종료 후 저장하세요.')
            return None
        self._begin_input_block()
        try:
            path = filedialog.asksaveasfilename(title = '설정 저장', defaultextension = '.json', filetypes = [
                ('JSON', '*.json')])
        finally:
            self._end_input_block()
        if not path:
            return None
        data = self._settings_payload()
        try:
            with open(path, 'w', encoding = 'utf-8') as f:
                json.dump(data, f, ensure_ascii = False, indent = 2)
            messagebox.showinfo('완료', '저장되었습니다.')
            return None
        except Exception as e:
            messagebox.showerror('오류', f'''저장 실패: {e}''')
            return None


    
    def _load(self):
        if self.running or self.triggers_enabled or self.paused_hold or self.loot_hold_active:
            messagebox.showwarning('안내', '실행 중이거나 일시정지/빠른클릭 중에는 불러오기를 할 수 없습니다. 종료 후 진행하세요.')
            return None
        self._begin_input_block()
        try:
            path = filedialog.askopenfilename(title = '설정 불러오기', filetypes = [
                ('JSON', '*.json')])
        finally:
            self._end_input_block()
        if not path:
            return None
        try:
            with open(path, 'r', encoding = 'utf-8') as f:
                data = json.load(f)
            self._apply_loaded_settings_data(data, show_warnings = True)
            self._refresh_start_key_var()
            self._refresh_stop_key_var()
            self._refresh_pause_key_var()
            self.loot_key_var.set(hotkey_display_text(self.loot_hold_key_str))
            self.quick_right_key_var.set(hotkey_display_text(self.quick_right_hold_key_str))
            self.start_stop_same_var.set(self.start_stop_same_key)
            if hasattr(self, 'center_status_var'):
                self.center_status_var.set(bool(self.center_status_enabled))
            self._refresh_active_program_var()
            self._sync_start_stop_same_key_ui()
            self._refresh_status_indicator(force = True)
            self._refresh_tree()
            self._refresh_trigger_tree()
            messagebox.showinfo('완료', '불러오기 완료.')
            return None
        except Exception as e:
            messagebox.showerror('오류', f'''불러오기 실패: {e}''')
            return None


    
    def _start_macro(self):
        with self._run_lock:
            if self.running or self.triggers_enabled:
                return None
            has_repeat_actions = bool(self.actions)
            has_trigger_actions = bool(self.trigger_actions)
            if not has_repeat_actions and not has_trigger_actions:
                self.status_var.set('반복 키/자동 순차 실행이 없습니다. 반복키추가 또는 자동순차실행추가를 먼저 등록하세요.')
                return None
            if not self._is_active_program_allowed():
                self._apply_hold_stop()
                self.status_var.set('동작시킬 프로그램이 현재 활성창이 아닙니다. 선택한 프로그램 창에서 시작하세요.')
                return None
            self.running = has_repeat_actions
            self.triggers_enabled = has_trigger_actions
            self.paused_hold = False
            self._triggers_enabled_before_pause = False
            self._pressed_pause_inputs.clear()
            self._toggle_pause_active_key = ''
            with self._trigger_lock:
                self._pressed_trigger_keys.clear()
                self._pressed_trigger_mouse_inputs.clear()
                self._active_trigger_ids.clear()
                self._trigger_run_versions.clear()
                self._suppressed_trigger_inputs.clear()
            self._trigger_epoch += 1
            self._held_mouse = []
            self._worker_threads = []
            if has_repeat_actions:
                for a in self.actions:
                    if not a.get('mode') == 'hold':
                        continue
                    self._apply_hold_start(a)
                for a in self.actions:
                    if not a.get('mode') == 'click':
                        continue
                    t = threading.Thread(target = self._click_worker, args = (a,), daemon = True)
                    self._worker_threads.append(t)
                    t.start()
            if self.running and self.triggers_enabled:
                self.status_var.set('실행중 (반복 키/자동 순차 실행 활성화, 종료키로 모두 중지)')
            elif self.running:
                self.status_var.set('실행중 (반복 키만 활성화, 종료키로 중지)')
            else:
                self.status_var.set('자동 순차 실행 활성화중 (종료키로 중지)')
            return None
    def _stop_macro(self):
        with self._run_lock:
            if not self.running and not self.triggers_enabled and not self.paused_hold and not self.loot_hold_active:
                return None
            self.running = False
            self.triggers_enabled = False
            self.paused_hold = False
            self.loot_hold_active = False
            self.quick_click_active = False
            self.quick_click_button = ''
            self._triggers_enabled_before_pause = False
            self._loot_triggers_enabled_before = False
            self._pressed_pause_inputs.clear()
            self._toggle_pause_active_key = ''
            with self._trigger_lock:
                self._pressed_trigger_keys.clear()
                self._pressed_trigger_mouse_inputs.clear()
                self._active_trigger_ids.clear()
                self._trigger_run_versions.clear()
                self._suppressed_trigger_inputs.clear()
                self._trigger_epoch += 1
        for _ in range(30):
            alive = any((t.is_alive() for t in self._worker_threads))
            if not alive:
                break
            else:
                time.sleep(0.05)
        self._apply_hold_stop()
        self.status_var.set('대기중 (시작키를 누르면 반복 키/자동 순차 실행 시작, 종료키로 모두 중지)')
        return None

    
    def _apply_hold_start(self = None, a = None):
        if not self._is_active_program_allowed():
            return None
        if a['type'] == 'key':
            ks = a.get('key', '')
            if ks.startswith('Gamepad.'):
                if self._pad_press(ks):
                    self._held_pad.append(ks)
                return None
            kobj = str_to_key(ks)
            if kobj is None:
                return None
            try:
                self.kb_controller.press(kobj)
                self._held_keys.append(kobj)
            except Exception:
                return None
        else:
            (button_type, button) = self._action_mouse_storage(a)
            bobj = mouse_button_obj_from_storage(button_type, button)
            if bobj is None:
                return None
            try:
                self.mouse_controller.press(bobj)
                self._held_mouse.append(bobj)
            except Exception:
                return None


    
    def _apply_hold_stop(self):
        for kobj in self._held_keys:
            try:
                self.kb_controller.release(kobj)
            except Exception:
                continue
        self._held_keys = []
        for bobj in self._held_mouse:
            try:
                self.mouse_controller.release(bobj)
            except Exception:
                continue
        self._held_mouse = []
        for name in self._held_pad:
            try:
                self.virtual_pad.release(name)
            except Exception:
                continue
        self._held_pad = []
        return None


    def _pad_output(self, ks, tap):
        vp = self.virtual_pad
        if vp is None or not vp.supported:
            self.status_var.set('게임패드 출력 기능이 이 빌드에 없습니다. 최신 빌드로 업데이트하세요.')
            return False
        ok = vp.tap(ks) if tap else vp.press(ks)
        if not ok:
            err = getattr(vp, 'last_error', None)
            msg = '게임패드 출력 실패: ViGEmBus 드라이버 인식 안됨(설치 후 재부팅 필요).'
            if err:
                msg += ' [' + str(err) + ']'
            self.status_var.set(msg)
        return ok


    def _pad_press(self, ks):
        return self._pad_output(ks, False)


    def _pad_tap(self, ks):
        return self._pad_output(ks, True)


    def _click_worker(self = None, a = None):
        try:
            interval = parse_interval(str(a.get('interval', 0.0001)))
        except Exception:
            interval = 0.0001
        while True:
            if not self.running:
                return None
            while self.running and (self.paused_hold or self.loot_hold_active or self._is_input_blocked()):
                time.sleep(0.02)
            if not self.running:
                return None
            if not self._is_active_program_allowed():
                self._enforce_active_program_guard()
                time.sleep(0.03)
                continue
            try:
                if a['type'] == 'key':
                    ks = a.get('key', '')
                    if ks.startswith('Gamepad.'):
                        self._pad_tap(ks)
                    else:
                        kobj = str_to_key(ks)
                        if kobj is not None:
                            self.kb_controller.press(kobj)
                            self.kb_controller.release(kobj)
                else:
                    (button_type, button) = self._action_mouse_storage(a)
                    bobj = mouse_button_obj_from_storage(button_type, button)
                    if bobj is not None:
                        self.mouse_controller.press(bobj)
                        self.mouse_controller.release(bobj)
            except Exception:
                pass
            t0 = time.time()
            while True:
                if not self.running:
                    return None
                while self.running and (self.paused_hold or self.loot_hold_active or self._is_input_blocked()):
                    time.sleep(0.02)
                if not self.running:
                    return None
                elapsed = time.time() - t0
                if elapsed >= interval:
                    break
                remaining = interval - elapsed
                time.sleep(min(0.001, max(0.0001, remaining)))

    
    def _start_loot_hold(self):
        self._start_quick_click_hold('left')

    
    def _stop_loot_hold(self):
        if self.quick_click_button == 'left':
            self._stop_quick_click_hold()
            return None

    
    def _start_quick_right_hold(self):
        self._start_quick_click_hold('right')

    
    def _stop_quick_right_hold(self):
        if self.quick_click_button == 'right':
            self._stop_quick_click_hold()
            return None

    
    def _start_quick_click_hold(self = None, button_name = None):
        with self._run_lock:
            if self.quick_click_active or self.loot_hold_active:
                return None
            if button_name not in frozenset({'left', 'right'}):
                return None
            if not self._is_active_program_allowed():
                self._apply_hold_stop()
                self.status_var.set('동작시킬 프로그램이 현재 활성창이 아닙니다. 빠른클릭을 실행하지 않습니다.')
                return None
            self.quick_click_active = True
            self.quick_click_button = button_name
            self.loot_hold_active = True
            self._loot_triggers_enabled_before = self.triggers_enabled
            with self._trigger_lock:
                self._pressed_trigger_keys.clear()
                self._pressed_trigger_mouse_inputs.clear()
                self._suppressed_trigger_inputs.clear()
            self._apply_hold_stop()
            self._loot_click_thread = threading.Thread(target = self._loot_click_worker, daemon = True)
            self._loot_click_thread.start()
            if button_name == 'right':
                if self.running or self._loot_triggers_enabled_before:
                    self.status_var.set('빠른우클릭중 (기존 매크로 임시정지, 빠른우클릭키를 떼면 재개)')
                else:
                    self.status_var.set('빠른우클릭중 (우클릭 반복, 빠른우클릭키를 떼면 정지)')
            elif self.running or self._loot_triggers_enabled_before:
                self.status_var.set('루팅중 (기존 매크로 임시정지, 루팅키를 떼면 재개)')
            else:
                self.status_var.set('루팅중 (좌클릭 반복, 루팅키를 떼면 정지)')
            return None
    def _stop_quick_click_hold(self):
        with self._run_lock:
            if not self.quick_click_active and not self.loot_hold_active:
                return None
            self.quick_click_active = False
            self.quick_click_button = ''
            self.loot_hold_active = False
            if not self.paused_hold:
                self.triggers_enabled = self._loot_triggers_enabled_before
            self._loot_triggers_enabled_before = False
            if self.running and not self.paused_hold:
                for a in self.actions:
                    if not a.get('mode') == 'hold':
                        continue
                    self._apply_hold_start(a)
            if self.paused_hold:
                self.status_var.set('일시정지중 (반복 키/자동 순차 실행 모두 중지, 일시정지키를 모두 떼면 재개)')
            elif self.running and self.triggers_enabled:
                self.status_var.set('실행중 (반복 키/자동 순차 실행 활성화, 종료키로 모두 중지)')
            elif self.running:
                self.status_var.set('실행중 (반복 키만 활성화, 종료키로 중지)')
            elif self.triggers_enabled:
                self.status_var.set('자동 순차 실행 활성화중 (종료키로 중지)')
            else:
                self.status_var.set('대기중 (시작키를 누르면 반복 키/자동 순차 실행 시작, 종료키로 모두 중지)')
            return None
    def _loot_click_worker(self):
        button_name = self.quick_click_button if self.quick_click_button in frozenset({'left', 'right'}) else 'left'
        bobj = mouse_button_obj_from_storage('basic', button_name)
        if bobj is None:
            return None
        while self.loot_hold_active and self.quick_click_active:
            if not self._is_active_program_allowed():
                self._enforce_active_program_guard()
                time.sleep(0.03)
                continue
            try:
                self.mouse_controller.press(bobj)
                self.mouse_controller.release(bobj)
            except Exception:
                pass
            t0 = time.time()
            while self.loot_hold_active and self.quick_click_active:
                elapsed = time.time() - t0
                if elapsed >= self._loot_click_interval:
                    break
                remaining = self._loot_click_interval - elapsed
                time.sleep(min(0.001, max(0.0001, remaining)))
        return None

    def _fire_trigger(self = None, trigger_type = None, trigger_value = None):
        if not self.triggers_enabled:
            return None
        if not self._is_active_program_allowed():
            self._enforce_active_program_guard()
            return None
        if not self.trigger_actions:
            return None
        matched = []
        for a in self.trigger_actions:
            if a.get('trigger_type') != trigger_type:
                continue
            if not self._trigger_action_input_value(a) == trigger_value:
                continue
            matched.append(a)
        if not matched:
            return None
        for a in matched:
            trigger_id = a.get('id', '')
            execution_mode = a.get('execution_mode', 'once')
            run_mode = a.get('run_mode', 'skip_while_running')
            always_mode = a.get('always_mode', 'append')
            run_token = None
            if execution_mode == 'hold_while_pressed':
                allow_first_cycle = a.get('hold_stop_mode', 'stop_immediately') == 'finish_current'
                with self._trigger_lock:
                    if trigger_id in self._active_trigger_ids:
                        continue
                    if trigger_id:
                        self._active_trigger_ids.add(trigger_id)
                    epoch = self._trigger_epoch
                t = threading.Thread(target = self._trigger_worker, args = (a, epoch, trigger_id, run_token, allow_first_cycle), daemon = True)
                t.start()
                continue
            if execution_mode == 'repeat' and run_mode == 'always' and always_mode == 'append':
                always_mode = 'restart'
            with self._trigger_lock:
                if run_mode == 'skip_while_running' and trigger_id in self._active_trigger_ids:
                    continue
                if run_mode == 'skip_while_running':
                    if trigger_id:
                        self._active_trigger_ids.add(trigger_id)
                elif run_mode == 'always' and always_mode == 'restart' and trigger_id:
                    next_version = int(self._trigger_run_versions.get(trigger_id, 0)) + 1
                    self._trigger_run_versions[trigger_id] = next_version
                    run_token = next_version
                epoch = self._trigger_epoch
            t = threading.Thread(target = self._trigger_worker, args = (a, epoch, trigger_id, run_token, False), daemon = True)
            t.start()
        return None

    
    def _trigger_is_active(self = None, epoch = None, trigger_id = None, run_token = ('', None)):
        with self._trigger_lock:
            if not self.triggers_enabled:
                return False
            if epoch != self._trigger_epoch:
                return False
            if trigger_id and run_token is not None:
                return self._trigger_run_versions.get(trigger_id) == run_token
            return True

    def _trigger_worker(self, a = None, epoch = None, trigger_id = None, run_token = None, allow_first_cycle = None):
        steps = self._trigger_steps(a)
        if not steps:
            if trigger_id:
                with self._trigger_lock:
                    self._active_trigger_ids.discard(trigger_id)
            return None
        execution_mode = a.get('execution_mode', 'once')
        hold_stop_mode = a.get('hold_stop_mode', 'stop_immediately')
        trigger_type = a.get('trigger_type', 'key')
        trigger_value = self._trigger_action_input_value(a)
        ordered_steps = sorted(steps, key = (lambda x: float(x.get('delay', 0.0001))))
        first_cycle_allowed = bool(allow_first_cycle)
        while True:
            while self.paused_hold or self.loot_hold_active or self._is_input_blocked():
                if not self._trigger_is_active(epoch, trigger_id, run_token):
                    if trigger_id:
                        with self._trigger_lock:
                            self._active_trigger_ids.discard(trigger_id)
                    return None
                time.sleep(0.02)
            if execution_mode == 'hold_while_pressed' and not self._is_trigger_input_pressed(trigger_type, trigger_value) and not first_cycle_allowed:
                if trigger_id:
                    with self._trigger_lock:
                        self._active_trigger_ids.discard(trigger_id)
                return None
            start_time = time.time()
            if execution_mode == 'repeat' and bool(a.get('repeat_include_trigger', False)):
                self._perform_trigger_start_output(a, epoch, trigger_id, run_token)
            for step in ordered_steps:
                try:
                    delay = parse_interval(str(step.get('delay', 0.0001)))
                except Exception:
                    delay = 0.0001
                while time.time() - start_time < delay:
                    if not self._trigger_is_active(epoch, trigger_id, run_token):
                        if trigger_id:
                            with self._trigger_lock:
                                self._active_trigger_ids.discard(trigger_id)
                        return None
                    if execution_mode == 'hold_while_pressed' and hold_stop_mode == 'stop_immediately' and not self._is_trigger_input_pressed(trigger_type, trigger_value):
                        if trigger_id:
                            with self._trigger_lock:
                                self._active_trigger_ids.discard(trigger_id)
                        return None
                    if self.paused_hold or self.loot_hold_active or self._is_input_blocked():
                        pause_started = time.time()
                        while self.paused_hold or self.loot_hold_active or self._is_input_blocked():
                            if not self._trigger_is_active(epoch, trigger_id, run_token):
                                if trigger_id:
                                    with self._trigger_lock:
                                        self._active_trigger_ids.discard(trigger_id)
                                return None
                            time.sleep(0.02)
                        start_time += time.time() - pause_started
                        continue
                    elapsed = time.time() - start_time
                    remaining = delay - elapsed
                    time.sleep(min(0.001, max(0.0001, remaining)))
                if not self._trigger_is_active(epoch, trigger_id, run_token):
                    if trigger_id:
                        with self._trigger_lock:
                            self._active_trigger_ids.discard(trigger_id)
                    return None
                if execution_mode == 'hold_while_pressed' and hold_stop_mode == 'stop_immediately' and not self._is_trigger_input_pressed(trigger_type, trigger_value):
                    if trigger_id:
                        with self._trigger_lock:
                            self._active_trigger_ids.discard(trigger_id)
                    return None
                while self.paused_hold or self.loot_hold_active or self._is_input_blocked():
                    if not self._trigger_is_active(epoch, trigger_id, run_token):
                        if trigger_id:
                            with self._trigger_lock:
                                self._active_trigger_ids.discard(trigger_id)
                        return None
                    time.sleep(0.02)
                self._perform_trigger_step_output(step, epoch, trigger_id, run_token)
            if execution_mode == 'once':
                break
            if execution_mode == 'hold_while_pressed':
                first_cycle_allowed = False
                if not self._is_trigger_input_pressed(trigger_type, trigger_value):
                    break
            if not self._trigger_is_active(epoch, trigger_id, run_token):
                if trigger_id:
                    with self._trigger_lock:
                        self._active_trigger_ids.discard(trigger_id)
                return None
            time.sleep(0.001)
        if trigger_id:
            with self._trigger_lock:
                self._active_trigger_ids.discard(trigger_id)
        return None
    def _perform_trigger_start_output(self = None, a = None, epoch = None, trigger_id = None, run_token = None):
        try:
            if not self._trigger_is_active(epoch, trigger_id, run_token):
                return None
            if not self._is_active_program_allowed():
                self._enforce_active_program_guard()
                return None
            trigger_type = a.get('trigger_type', 'key')
            if trigger_type == 'key':
                ks = a.get('trigger_key', '')
                if ks.startswith('Gamepad.'):
                    self._suppress_next_trigger_input('key', ks)
                    self._pad_tap(ks)
                else:
                    kobj = str_to_key(ks)
                    if kobj is not None:
                        self._suppress_next_trigger_input('key', ks)
                        self.kb_controller.press(kobj)
                        self.kb_controller.release(kobj)
            else:
                (button_type, button) = self._trigger_action_mouse_storage(a)
                bobj = mouse_button_obj_from_storage(button_type, button)
                mouse_input = mouse_button_hotkey(button, button_type)
                if bobj is not None:
                    if mouse_input:
                        self._suppress_next_trigger_input('mouse', mouse_input)
                        self.mouse_controller.press(bobj)
                        self.mouse_controller.release(bobj)
        except Exception:
            return None

    
    def _perform_trigger_step_output(self = None, step = None, epoch = None, trigger_id = None, run_token = None):
        try:
            if not self._trigger_is_active(epoch, trigger_id, run_token):
                return None
            if not self._is_active_program_allowed():
                self._enforce_active_program_guard()
                return None
            target_type = step.get('target_type', 'key')
            if target_type == 'key':
                ks = step.get('target_key', '')
                if ks.startswith('Gamepad.'):
                    self._pad_tap(ks)
                else:
                    kobj = str_to_key(ks)
                    if kobj is not None:
                        self.kb_controller.press(kobj)
                        self.kb_controller.release(kobj)
            else:
                (button_type, button) = self._trigger_step_mouse_storage(step)
                bobj = mouse_button_obj_from_storage(button_type, button)
                if bobj is not None:
                    self.mouse_controller.press(bobj)
                    self.mouse_controller.release(bobj)
        except Exception:
            return None



class ActiveProgramDialog(tk.Toplevel):
    
    def __init__(self = None, master = None):
        super().__init__(master)
        self.master = master
        self._input_block_closed = False
        self.master._begin_input_block()
        self.title('동작시킬 프로그램')
        self.master._center_child_window(self, 660, 560)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.programs = []
        self.target_vars = { }
        self.target_checks = []
        self.all_var = tk.BooleanVar(value = bool(master.active_program_all))
        self._build()

    
    def _build(self):
        root = ttk.Frame(self, padding = 12)
        root.pack(fill = 'both', expand = True)
        ttk.Label(root, text = '동작시킬 프로그램', font = ('', 12, 'bold')).pack(anchor = 'w')
        ttk.Label(root, text = '전체를 선택하면 기존처럼 모든 프로그램에서 동작합니다. 특정 프로그램을 선택하면 현재 활성창이 선택한 프로그램일 때만 매크로가 동작합니다.', wraplength = 620).pack(anchor = 'w', pady = (4, 10))
        top_box = ttk.LabelFrame(root, text = '기본 설정', padding = 10)
        top_box.pack(fill = 'x')
        ttk.Checkbutton(top_box, text = '전체', variable = self.all_var, command = self._sync_state).pack(anchor = 'w')
        list_box = ttk.LabelFrame(root, text = '현재 실행 중인 프로그램', padding = 10)
        list_box.pack(fill = 'both', expand = True, pady = (10, 0))
        self.list_content = self.master._create_vertical_scroll_area(list_box)
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (12, 0))
        ttk.Button(btns, text = '목록 새로고침', command = self._reload_programs).pack(side = 'left')
        ttk.Button(btns, text = '취소', command = self._close).pack(side = 'right')
        ttk.Button(btns, text = '확인', command = self._submit).pack(side = 'right', padx = (0, 8))
        self._reload_programs()

    
    def _reload_programs(self):
        selected_before = set()
        for process_name, var in self.target_vars.items():
            if bool(var.get()):
                selected_before.add(process_name.lower())
        if not selected_before:
            selected_before = {item.lower() for item in self.master._normalize_active_program_targets(self.master.active_program_targets)}
        for child in self.list_content.winfo_children():
            child.destroy()
        self.programs = enumerate_running_window_programs()
        existing_names = {str(item.get('process', '')).lower() for item in self.programs}
        for saved_process in self.master._normalize_active_program_targets(self.master.active_program_targets):
            key = saved_process.lower()
            if not key:
                continue
            if key in existing_names:
                continue
            self.programs.append({
                'process': saved_process,
                'title': '현재 실행 목록에 없음',
                'display': f'''{saved_process} - 현재 실행 목록에 없음''' })
            existing_names.add(key)
        self.programs = sorted(self.programs, key = active_program_sort_key)
        self.target_vars = { }
        self.target_checks = []
        if not self.programs:
            ttk.Label(self.list_content, text = '현재 표시할 수 있는 프로그램 창이 없습니다. 프로그램을 실행한 뒤 목록 새로고침을 눌러주세요.', wraplength = 580).pack(anchor = 'w', pady = 8)
            self._sync_state()
            return None
        for item in self.programs:
            process_name = normalize_program_process_name(item.get('process', ''))
            if not process_name:
                continue
            display_text = str(item.get('display', process_name))
            var = tk.BooleanVar(value = process_name.lower() in selected_before)
            self.target_vars[process_name] = var
            check = ttk.Checkbutton(self.list_content, text = display_text, variable = var)
            check.pack(anchor = 'w', fill = 'x', pady = 2)
            self.target_checks.append(check)
        self._sync_state()
        return None
        

    
    def _sync_state(self):
        try:
            disabled = bool(self.all_var.get())
            state = 'disabled' if disabled else 'normal'
            for check in self.target_checks:
                check.configure(state = state)
            return None
        except Exception:
            pass


    def _selected_targets(self = None):
        selected = []
        for process_name, var in self.target_vars.items():
            try:
                if bool(var.get()):
                    selected.append(process_name)
            except Exception:
                continue
        return self.master._normalize_active_program_targets(selected)

    
    def _submit(self):
        selected = self._selected_targets()
        if bool(self.all_var.get()) or not selected:
            self.master.active_program_all = True
            self.master.active_program_targets = []
        else:
            self.master.active_program_all = False
            self.master.active_program_targets = selected
        self.master._active_program_blocked = False
        self.master._refresh_active_program_var()
        self.master._refresh_status_indicator(force = True)
        self._close()

    
    def _close(self):
        if not self._input_block_closed:
            self._input_block_closed = True
            self.master._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None




class CenterStatusSettingsDialog(tk.Toplevel):
    
    def __init__(self = None, master = None):
        super().__init__(master)
        self.master = master
        self._input_block_closed = False
        self.master._begin_input_block()
        self.title('상태표시 설정')
        self.master._center_child_window(self, 640, 560)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self._original_center_status_targets = list(master._normalize_center_status_targets())
        self._original_center_status_shape = master.center_status_shape if master.center_status_shape in frozenset({'bar', 'circle'}) else 'circle'
        self._original_center_status_show_text = bool(master.center_status_show_text)
        self._original_center_status_size_percent = master._center_status_size_percent_value()
        self._is_submitted = False
        self.target_vars = { }
        self.shape_var = tk.StringVar(value = self._original_center_status_shape)
        self.show_text_var = tk.BooleanVar(value = self._original_center_status_show_text)
        self.size_percent_var = tk.IntVar(value = self._original_center_status_size_percent)
        self.size_percent_label_var = tk.StringVar(value = f'''{self._original_center_status_size_percent}%''')
        self._build()

    
    def _build(self):
        root = ttk.Frame(self, padding = 12)
        root.pack(fill = 'both', expand = True)
        title = ttk.Label(root, text = '상태표시 설정', font = ('', 12, 'bold'))
        title.pack(anchor = 'w', pady = (0, 10))
        target_box = ttk.LabelFrame(root, text = '상태표시 위치', padding = 10)
        target_box.pack(fill = 'x')
        current_targets = set(self.master._normalize_center_status_targets())
        monitors = self.master._enumerate_display_monitors()
        for monitor in monitors:
            target = monitor['target']
            width = int(monitor['right']) - int(monitor['left'])
            height = int(monitor['bottom']) - int(monitor['top'])
            primary_text = ' / 주 모니터' if monitor.get('primary') else ''
            label = f'''{monitor['label']} - {width}x{height} / 위치 {monitor['left']},{monitor['top']}{primary_text}'''
            var = tk.BooleanVar(value = target in current_targets)
            self.target_vars[target] = var
            ttk.Checkbutton(target_box, text = label, variable = var, command = self._apply_preview).pack(anchor = 'w', pady = 2)
        shape_box = ttk.LabelFrame(root, text = '상태표시 표시 방식', padding = 10)
        shape_box.pack(fill = 'x', pady = (10, 0))
        ttk.Radiobutton(shape_box, text = '원형', value = 'circle', variable = self.shape_var, command = self._apply_preview).pack(anchor = 'w', pady = 2)
        ttk.Radiobutton(shape_box, text = '가로막대형', value = 'bar', variable = self.shape_var, command = self._apply_preview).pack(anchor = 'w', pady = 2)
        ttk.Checkbutton(shape_box, text = '실행중 / 일시정지 / 대기중 텍스트 추가표시', variable = self.show_text_var, command = self._apply_preview).pack(anchor = 'w', pady = (6, 2))
        size_box = ttk.LabelFrame(root, text = '상태표시 크기', padding = 10)
        size_box.pack(fill = 'x', pady = (10, 0))
        size_row = ttk.Frame(size_box)
        size_row.pack(fill = 'x')
        ttk.Label(size_row, text = '작게').pack(side = 'left')
        scale = ttk.Scale(size_row, from_ = 50, to = 200, orient = 'horizontal', command = self._on_size_scale_change)
        scale.set(self.size_percent_var.get())
        scale.pack(side = 'left', fill = 'x', expand = True, padx = 10)
        self.size_scale = scale
        ttk.Label(size_row, text = '크게').pack(side = 'left')
        ttk.Label(size_box, textvariable = self.size_percent_label_var).pack(anchor = 'center', pady = (6, 0))
        info_text = '기본값은 현재 상태표시 크기 기준 100%입니다. 여러 위치를 체크하면 선택된 각 모니터 중앙에 상태표시가 각각 표시됩니다.'
        ttk.Label(root, text = info_text, wraplength = 580).pack(anchor = 'w', pady = (10, 0))
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (14, 0))
        ttk.Button(btns, text = '취소', command = self._close).pack(side = 'right')
        ttk.Button(btns, text = '확인', command = self._submit).pack(side = 'right', padx = (0, 8))

    
    def _on_size_scale_change(self, value):
        
        try:
            size_percent = int(round(float(value)))
        except Exception:
            size_percent = 100

        size_percent = max(50, min(200, size_percent))
        self.size_percent_var.set(size_percent)
        self.size_percent_label_var.set(f'''{size_percent}%''')
        self._apply_preview()

    
    def _apply_preview(self):
        self.master.center_status_targets = self.master._normalize_center_status_targets(self._selected_targets())
        self.master.center_status_shape = self.shape_var.get() if self.shape_var.get() in frozenset({'bar', 'circle'}) else 'circle'
        self.master.center_status_show_text = bool(self.show_text_var.get())
        
        try:
            size_percent = int(self.size_percent_var.get() or 100)
        except Exception:
            size_percent = 100

        self.master.center_status_size_percent = max(50, min(200, size_percent))
        self.master._refresh_status_indicator(force = True)

    
    def _restore_original(self):
        self.master.center_status_targets = list(self._original_center_status_targets)
        self.master.center_status_shape = self._original_center_status_shape
        self.master.center_status_show_text = bool(self._original_center_status_show_text)
        self.master.center_status_size_percent = int(self._original_center_status_size_percent)
        self.master._refresh_status_indicator(force = True)

    
    def _selected_targets(self = None):
        selected = []
        for target, var in self.target_vars.items():
            try:
                if bool(var.get()):
                    selected.append(target)
            except Exception:
                continue
        if selected:
            return selected
        return [
            'window']

    
    def _submit(self):
        self._apply_preview()
        self._is_submitted = True
        self._close()

    
    def _close(self):
        if not self._is_submitted:
            self._restore_original()
        if not self._input_block_closed:
            self._input_block_closed = True
            self.master._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None




class HotkeyListDialog(tk.Toplevel):
    
    def __init__(self = None, master = None, title = None, kind = None):
        super().__init__(master)
        self.master = master
        self.kind = kind
        self._input_block_closed = False
        self.master._begin_input_block()
        self.title(title)
        self.master._center_child_window(self, 520, 380)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.keys = list(master.start_keys if kind == 'start' else master.stop_keys)
        self._build()

    
    def _build(self):
        root = ttk.Frame(self, padding = 12)
        root.pack(fill = 'both', expand = True)
        title_text = '시작키 목록' if self.kind == 'start' else '종료키 목록'
        guide_text = '등록된 시작키 중 하나를 누르면 매크로가 시작됩니다.'
        if self.kind == 'stop':
            guide_text = '등록된 종료키 중 하나를 누르면 실행 중인 기능이 모두 중지됩니다.'
        ttk.Label(root, text = title_text, font = ('', 12, 'bold')).pack(anchor = 'w')
        ttk.Label(root, text = guide_text).pack(anchor = 'w', pady = (4, 10))
        list_box = ttk.LabelFrame(root, text = '목록', padding = 10)
        list_box.pack(fill = 'both', expand = True)
        self.tree = ttk.Treeview(list_box, columns = ('key',), show = 'headings', selectmode = 'browse', height = 8)
        self.tree.heading('key', text = '키')
        self.tree.column('key', width = 420, anchor = 'center')
        self.tree.pack(side = 'left', fill = 'both', expand = True)
        sc = ttk.Scrollbar(list_box, orient = 'vertical', command = self.tree.yview)
        self.tree.configure(yscrollcommand = sc.set)
        sc.pack(side = 'right', fill = 'y')
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (10, 0))
        ttk.Button(btns, text = '추가', command = self._add_key).pack(side = 'left')
        ttk.Button(btns, text = '편집', command = self._edit_key).pack(side = 'left', padx = 8)
        ttk.Button(btns, text = '삭제', command = self._delete_key).pack(side = 'left')
        ttk.Button(btns, text = '닫기', command = self._close).pack(side = 'right')
        self._refresh()

    
    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, key in enumerate(self.keys):
            self.tree.insert('', 'end', iid = str(idx), values = (hotkey_display_text(key),))

    
    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        
        try:
            return int(sel[0])
        except Exception:
            return None


    
    def _validate_key(self = None, key = None, editing_index = None):
        if not key:
            messagebox.showwarning('안내', '등록할 키를 선택하세요.')
            return False
        for idx, existing in enumerate(self.keys):
            if editing_index is not None and idx == editing_index:
                continue
            if not existing == key:
                continue
            messagebox.showwarning('경고', '이미 등록된 키입니다.')
            enumerate(self.keys)
            return False
        pause_values = self.master._pause_key_values()
        if key in pause_values:
            messagebox.showwarning('경고', '시작키/종료키는 일시정지키와 다르게 설정하세요.')
            return False
        if key == self.master.loot_hold_key_str or key == self.master.quick_right_hold_key_str:
            messagebox.showwarning('경고', '시작키/종료키는 빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
            return False
        if self.kind == 'start' and self.master.start_stop_same_key and key in self.master.stop_keys:
            messagebox.showwarning('경고', '시작키는 종료키와 다르게 설정하세요.')
            return False
        if self.kind == 'stop' and key in self.master.start_keys:
            messagebox.showwarning('경고', '종료키는 시작키와 다르게 설정하세요.')
            return False
        return True

    
    def _apply_keys_to_master(self):
        if not self.keys:
            self.keys = [
                'Key.f1' if self.kind == 'start' else 'Key.f2']
        if self.kind == 'start':
            self.master.start_keys = list(self.keys)
            if self.master.start_stop_same_key:
                self.master.stop_keys = list(self.keys)
            self.master._refresh_start_key_var()
            self.master._refresh_stop_key_var()
            self.master._sync_start_stop_same_key_ui()
        else:
            self.master.stop_keys = list(self.keys)
            self.master._refresh_stop_key_var()
        self.master._sync_legacy_hotkey_values()

    
    def _add_key(self):
        
        def done(key = None):
            if not self._validate_key(key):
                return None
            self.keys.append(key)
            self._apply_keys_to_master()
            self._refresh()

        self.master._capture_one_hotkey('키 추가', done)

    
    def _edit_key(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo('안내', '편집할 키를 선택하세요.')
            return None
        
        def done(key = None):
            if not self._validate_key(key, editing_index = idx):
                return None
            self.keys[idx] = key
            self._apply_keys_to_master()
            self._refresh()

        self.master._capture_one_hotkey('키 편집', done)

    
    def _delete_key(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo('안내', '삭제할 키를 선택하세요.')
            return None
        if len(self.keys) <= 1:
            messagebox.showwarning('안내', '키는 최소 1개 이상 필요합니다.')
            return None
        self.keys.pop(idx)
        self._apply_keys_to_master()
        self._refresh()

    
    def _close(self):
        if not self.keys:
            self.keys = [
                'Key.f1' if self.kind == 'start' else 'Key.f2']
            self._apply_keys_to_master()
        if not self._input_block_closed:
            self._input_block_closed = True
            self.master._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None




class PauseKeysDialog(tk.Toplevel):
    
    def __init__(self = None, master = None):
        super().__init__(master)
        self.master = master
        self._input_block_closed = False
        self.master._begin_input_block()
        self.title('일시정지키 설정')
        self.master._center_child_window(self, 620, 500)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.pause_key_items = [dict(item) for item in master.pause_key_items]
        self._build()
        return None
        

    
    def _build(self):
        root = ttk.Frame(self, padding = 12)
        root.pack(fill = 'both', expand = True)
        ttk.Label(root, text = '일시정지키 목록', font = ('', 12, 'bold')).pack(anchor = 'w')
        ttk.Label(root, text = '홀드 = 등록된 키 중 하나라도 누르고 있으면 일시정지됩니다.').pack(anchor = 'w', pady = (4, 2))
        ttk.Label(root, text = '토글 = 등록된 키를 한 번 누르면 일시정지 상태로 유지되고, 다시 동일한 키를 누르면 해제됩니다.').pack(anchor = 'w', pady = (0, 2))
        ttk.Label(root, text = '예시) C키를 토글로 등록한 경우: C 한 번 누름 → 일시정지 / C 다시 누름 → 가동').pack(anchor = 'w', pady = (0, 2))
        ttk.Label(root, text = '※ 주의사항: C키로 일시정지에 들어갔다면 다시 C키를 눌러야 일시정지가 해제됩니다.').pack(anchor = 'w', pady = (0, 10))
        list_box = ttk.LabelFrame(root, text = '목록', padding = 10)
        list_box.pack(fill = 'both', expand = True)
        self.tree = ttk.Treeview(list_box, columns = ('key', 'mode'), show = 'headings', selectmode = 'browse', height = 8)
        self.tree.heading('key', text = '일시정지키')
        self.tree.heading('mode', text = '방식')
        self.tree.column('key', width = 360, anchor = 'center')
        self.tree.column('mode', width = 120, anchor = 'center')
        self.tree.pack(side = 'left', fill = 'both', expand = True)
        sc = ttk.Scrollbar(list_box, orient = 'vertical', command = self.tree.yview)
        self.tree.configure(yscrollcommand = sc.set)
        sc.pack(side = 'right', fill = 'y')
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (10, 0))
        ttk.Button(btns, text = '추가', command = self._add_key).pack(side = 'left')
        ttk.Button(btns, text = '편집', command = self._edit_key).pack(side = 'left', padx = 8)
        ttk.Button(btns, text = '삭제', command = self._delete_key).pack(side = 'left')
        ttk.Button(btns, text = '닫기', command = self._close).pack(side = 'right')
        self._refresh()

    
    def _refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, item in enumerate(self.pause_key_items):
            self.tree.insert('', 'end', iid = str(idx), values = (hotkey_display_text(item.get('key', '')), self.master._pause_key_mode_label(item.get('mode', 'hold'))))

    
    def _selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        
        try:
            return int(sel[0])
        except Exception:
            return None


    
    def _validate_key(self = None, key = None, editing_index = None):
        if not key:
            messagebox.showwarning('안내', '등록할 키를 선택하세요.')
            return False
        if key in self.master.start_keys or key in self.master.stop_keys:
            messagebox.showwarning('경고', '일시정지키는 시작키/종료키와 다르게 설정하세요.')
            return False
        if key == self.master.loot_hold_key_str or key == self.master.quick_right_hold_key_str:
            messagebox.showwarning('경고', '일시정지키는 빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
            return False
        for idx, existing in enumerate(self.pause_key_items):
            if editing_index is not None and idx == editing_index:
                continue
            if not existing.get('key') == key:
                continue
            messagebox.showwarning('경고', '이미 등록된 일시정지키입니다.')
            enumerate(self.pause_key_items)
            return False
        return True

    
    def _apply_items_to_master(self):
        if not self.pause_key_items:
            self.pause_key_items = [
                {
                    'key': '`',
                    'mode': 'hold' }]
        self.master.pause_key_items = [dict(item) for item in self.pause_key_items]
        active_key = self.master._toggle_pause_active_key
        active_item = next((item for item in self.master.pause_key_items if item.get('key') == active_key and item.get('mode') == 'toggle'), None)
        if active_key and active_item is None:
            self.master._toggle_pause_active_key = ''
            if not self.master._pressed_pause_inputs:
                self.master._stop_pause_hold()
        self.master._refresh_pause_key_var()
        return None
        

    
    def _add_key(self):
        
        def done(item = None):
            key = item.get('key', '')
            if not self._validate_key(key):
                return None
            self.pause_key_items.append(item)
            self._apply_items_to_master()
            self._refresh()

        PauseKeyItemDialog(self, mode = 'add', initial = None, on_submit = done)

    
    def _edit_key(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo('안내', '편집할 일시정지키를 선택하세요.')
            return None
        
        def done(item = None):
            key = item.get('key', '')
            if not self._validate_key(key, editing_index = idx):
                return None
            self.pause_key_items[idx] = item
            self._apply_items_to_master()
            self._refresh()

        PauseKeyItemDialog(self, mode = 'edit', initial = self.pause_key_items[idx], on_submit = done)

    
    def _delete_key(self):
        idx = self._selected_index()
        if idx is None:
            messagebox.showinfo('안내', '삭제할 일시정지키를 선택하세요.')
            return None
        if len(self.pause_key_items) <= 1:
            messagebox.showwarning('안내', '일시정지키는 최소 1개 이상 필요합니다.')
            return None
        self.pause_key_items.pop(idx)
        self._apply_items_to_master()
        self._refresh()

    
    def _close(self):
        if not self.pause_key_items:
            self.pause_key_items = [
                {
                    'key': '`',
                    'mode': 'hold' }]
            self._apply_items_to_master()
        if not self._input_block_closed:
            self._input_block_closed = True
            self.master._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None




class PauseKeyItemDialog(tk.Toplevel):
    
    def __init__(self = None, parent = None, mode = None, initial = None, on_submit = None):
        super().__init__(parent)
        self.parent = parent
        self.master_app = parent.master
        self.mode = mode
        self.initial = initial or { }
        self.on_submit = on_submit
        self._input_block_closed = False
        self.master_app._begin_input_block()
        self.title('일시정지키 추가' if mode == 'add' else '일시정지키 편집')
        self.master_app._center_child_window(self, 460, 260)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.key_var = tk.StringVar(value = self.initial.get('key', ''))
        self.mode_var = tk.StringVar(value = 'toggle' if self.initial.get('mode') == 'toggle' else 'hold')
        self._build()

    
    def _build(self):
        root = ttk.Frame(self, padding = 12)
        root.pack(fill = 'both', expand = True)
        key_box = ttk.LabelFrame(root, text = '키', padding = 10)
        key_box.pack(fill = 'x')
        row = ttk.Frame(key_box)
        row.pack(fill = 'x')
        ttk.Entry(row, textvariable = self.key_var, width = 28, state = 'readonly', justify = 'center').pack(side = 'left', fill = 'x', expand = True)
        ttk.Button(row, text = '키 지정', command = self._pick_key).pack(side = 'left', padx = (8, 0))
        mode_box = ttk.LabelFrame(root, text = '방식', padding = 10)
        mode_box.pack(fill = 'x', pady = (10, 0))
        ttk.Radiobutton(mode_box, text = '홀드 - 누르고 있는 동안만 일시정지', value = 'hold', variable = self.mode_var).pack(anchor = 'w')
        ttk.Radiobutton(mode_box, text = '토글 - 한 번 누르면 일시정지, 같은 키를 다시 누르면 가동', value = 'toggle', variable = self.mode_var).pack(anchor = 'w', pady = (4, 0))
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (14, 0))
        ttk.Button(btns, text = '취소', command = self._close).pack(side = 'right')
        ttk.Button(btns, text = '확인', command = self._submit).pack(side = 'right', padx = (0, 8))

    
    def _pick_key(self):
        
        def done(key = None):
            self.key_var.set(key)

        self.master_app._capture_one_hotkey('일시정지키 지정', done)

    
    def _submit(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showwarning('안내', '일시정지키를 지정하세요.')
            return None
        self.on_submit({
            'key': key,
            'mode': 'toggle' if self.mode_var.get() == 'toggle' else 'hold' })
        self._close()

    
    def _close(self):
        if not self._input_block_closed:
            self._input_block_closed = True
            self.master_app._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None




class TriggerDialog(tk.Toplevel):
    
    def __init__(self = None, master = None, mode = None, initial = None, on_submit = None):
        super().__init__(master)
        self.master = master
        self.mode = mode
        self.initial = initial
        self.on_submit = on_submit
        self._input_block_closed = False
        self.master._begin_input_block()
        self.title('자동 순차 실행 추가' if mode == 'add' else '자동 순차 실행 편집')
        self.geometry('680x640')
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.id_value = initial['id'] if initial else uuid.uuid4().hex
        self.trigger_type_var = tk.StringVar(value = initial.get('trigger_type') if initial else 'key')
        self.trigger_key_var = tk.StringVar(value = initial.get('trigger_key') if initial else '')
        initial_trigger_button = initial.get('trigger_button') if initial else 'left'
        initial_trigger_button_type = normalize_mouse_button_type(initial.get('trigger_button_type') if initial else None, initial_trigger_button)
        self.trigger_mouse_choice_var = tk.StringVar(value = initial_trigger_button if initial_trigger_button_type == 'basic' else 'custom')
        self.trigger_custom_mouse_var = tk.StringVar(value = mouse_button_hotkey(initial_trigger_button, 'custom') if initial_trigger_button_type == 'custom' else '')
        self.execution_mode_var = tk.StringVar(value = initial.get('execution_mode') if initial else 'once')
        self.hold_stop_mode_var = tk.StringVar(value = initial.get('hold_stop_mode') if initial else 'stop_immediately')
        self.repeat_include_trigger_var = tk.BooleanVar(value = bool(initial.get('repeat_include_trigger', False)) if initial else False)
        self.run_mode_var = tk.StringVar(value = initial.get('run_mode') if initial else 'skip_while_running')
        self.always_mode_var = tk.StringVar(value = initial.get('always_mode') if initial else 'append')
        self.steps = []
        if initial:
            for step in master._trigger_steps(initial):
                clean_step = dict(step)
                clean_step['id'] = clean_step.get('id') or uuid.uuid4().hex
                self.steps.append(clean_step)
        self._build()

    
    def _build(self):
        dialog_root = ttk.Frame(self, padding = 12)
        dialog_root.pack(fill = 'both', expand = True)
        root = self.master._create_vertical_scroll_area(dialog_root)
        self._scroll_content = root
        ttk.Label(root, text = '자동 순차 실행', font = ('', 12)).pack(anchor = 'w')
        trigger_box = ttk.LabelFrame(root, text = '시작 조건', padding = 10)
        trigger_box.pack(fill = 'x', pady = (10, 0))
        trigger_type_row = ttk.Frame(trigger_box)
        trigger_type_row.pack(fill = 'x')
        ttk.Radiobutton(trigger_type_row, text = '키', value = 'key', variable = self.trigger_type_var, command = self._sync_state).pack(side = 'left')
        ttk.Radiobutton(trigger_type_row, text = '마우스', value = 'mouse', variable = self.trigger_type_var, command = self._sync_state).pack(side = 'left', padx = 14)
        trigger_key_row = ttk.Frame(trigger_box)
        trigger_key_row.pack(fill = 'x', pady = (8, 0))
        ttk.Label(trigger_key_row, text = '시작 키').pack(side = 'left')
        self.trigger_key_entry = ttk.Entry(trigger_key_row, textvariable = self.trigger_key_var, width = 22, state = 'readonly')
        self.trigger_key_entry.pack(side = 'left', padx = 8)
        self.trigger_key_button = ttk.Button(trigger_key_row, text = '키 지정', command = self._pick_trigger_key)
        self.trigger_key_button.pack(side = 'left')
        trigger_mouse_row = ttk.Frame(trigger_box)
        trigger_mouse_row.pack(fill = 'x', pady = (8, 0))
        ttk.Label(trigger_mouse_row, text = '시작 마우스').pack(side = 'left')
        
        def select_trigger_basic_mouse():
            self.trigger_custom_mouse_var.set('')

        self.trigger_mouse_left = ttk.Radiobutton(trigger_mouse_row, text = '왼쪽버튼', value = 'left', variable = self.trigger_mouse_choice_var, command = select_trigger_basic_mouse)
        self.trigger_mouse_left.pack(side = 'left', padx = 8)
        self.trigger_mouse_right = ttk.Radiobutton(trigger_mouse_row, text = '오른쪽버튼', value = 'right', variable = self.trigger_mouse_choice_var, command = select_trigger_basic_mouse)
        self.trigger_mouse_right.pack(side = 'left', padx = 8)
        self.trigger_mouse_middle = ttk.Radiobutton(trigger_mouse_row, text = '휠클릭', value = 'middle', variable = self.trigger_mouse_choice_var, command = select_trigger_basic_mouse)
        self.trigger_mouse_middle.pack(side = 'left', padx = 8)
        trigger_custom_row = ttk.Frame(trigger_box)
        trigger_custom_row.pack(fill = 'x', pady = 2)
        self.trigger_mouse_custom_radio = ttk.Radiobutton(trigger_custom_row, text = '그외 버튼', value = 'custom', variable = self.trigger_mouse_choice_var)
        self.trigger_mouse_custom_radio.pack(side = 'left')
        self.trigger_custom_entry = ttk.Entry(trigger_custom_row, textvariable = self.trigger_custom_mouse_var, width = 28, state = 'readonly')
        self.trigger_custom_entry.pack(side = 'left', padx = 8)
        self.trigger_custom_button = ttk.Button(trigger_custom_row, text = '그외 버튼추가', command = self._pick_trigger_custom_mouse)
        self.trigger_custom_button.pack(side = 'left')
        execution_mode_box = ttk.LabelFrame(root, text = '실행 형태', padding = 10)
        execution_mode_box.pack(fill = 'x', pady = (10, 0))
        ttk.Radiobutton(execution_mode_box, text = '시작키 누를 때마다 실행', value = 'once', variable = self.execution_mode_var, command = self._sync_state).pack(anchor = 'w')
        repeat_row = ttk.Frame(execution_mode_box)
        repeat_row.pack(fill = 'x', pady = (4, 0))
        ttk.Radiobutton(repeat_row, text = '반복실행', value = 'repeat', variable = self.execution_mode_var, command = self._sync_state).pack(side = 'left')
        self.repeat_include_trigger_check = ttk.Checkbutton(repeat_row, text = '시작키를 매 반복 첫 동작에 포함', variable = self.repeat_include_trigger_var)
        self.repeat_include_trigger_check.pack(side = 'left', padx = (14, 0))
        ttk.Radiobutton(execution_mode_box, text = '시작키 누르고 있는 동안 순차실행 동작', value = 'hold_while_pressed', variable = self.execution_mode_var, command = self._sync_state).pack(anchor = 'w', pady = (4, 0))
        run_mode_box = ttk.LabelFrame(root, text = '실행 방식', padding = 10)
        run_mode_box.pack(fill = 'x', pady = (10, 0))
        self.run_always_radio = ttk.Radiobutton(run_mode_box, text = '무조건실행(시작키 누를 때마다 무조건 실행)', value = 'always', variable = self.run_mode_var, command = self._sync_state)
        self.run_always_radio.pack(anchor = 'w')
        always_detail_box = ttk.Frame(run_mode_box)
        always_detail_box.pack(fill = 'x', padx = (24, 0), pady = (4, 0))
        ttk.Label(always_detail_box, text = '무조건 실행 세부설정(시작키 누를때 마다)').pack(anchor = 'w')
        self.always_restart_radio = ttk.Radiobutton(always_detail_box, text = '기존 순차실행 삭제후 실행', value = 'restart', variable = self.always_mode_var)
        self.always_restart_radio.pack(anchor = 'w', pady = (3, 0))
        self.always_append_radio = ttk.Radiobutton(always_detail_box, text = '기존 순차실행 유지후 추가실행', value = 'append', variable = self.always_mode_var)
        self.always_append_radio.pack(anchor = 'w', pady = (3, 0))
        self.run_skip_radio = ttk.Radiobutton(run_mode_box, text = '순차진행중미실행(순차 실행 중에는 시작키를 눌러도 무시)', value = 'skip_while_running', variable = self.run_mode_var, command = self._sync_state)
        self.run_skip_radio.pack(anchor = 'w', pady = (8, 0))
        self.run_hold_radio = ttk.Radiobutton(run_mode_box, text = '순차진행 중단 여부(시작키 누르고 있는 동안 순차실행 전용설정)', value = 'hold_while_pressed', variable = self.run_mode_var, command = self._sync_state)
        self.run_hold_radio.pack(anchor = 'w', pady = (8, 0))
        hold_stop_box = ttk.Frame(run_mode_box)
        hold_stop_box.pack(fill = 'x', padx = (24, 0), pady = (4, 0))
        self.hold_stop_now_radio = ttk.Radiobutton(hold_stop_box, text = '시작키 떼면 동작 중이던 순차실행 중지', value = 'stop_immediately', variable = self.hold_stop_mode_var)
        self.hold_stop_now_radio.pack(anchor = 'w', pady = (4, 0))
        self.hold_stop_finish_radio = ttk.Radiobutton(hold_stop_box, text = '시작키 떼면 동작 중이던 순차실행 완료 후 중지', value = 'finish_current', variable = self.hold_stop_mode_var)
        self.hold_stop_finish_radio.pack(anchor = 'w', pady = (3, 0))
        steps_box = ttk.LabelFrame(root, text = '실행할 동작', padding = 10)
        steps_box.pack(fill = 'both', expand = True, pady = (10, 0))
        step_cols = ('delay', 'target')
        self.steps_tree = ttk.Treeview(steps_box, columns = step_cols, show = 'headings', selectmode = 'browse', height = 8)
        self.steps_tree.heading('delay', text = '지연(초)')
        self.steps_tree.heading('target', text = '자동 실행')
        self.steps_tree.column('delay', width = 100, anchor = 'center')
        self.steps_tree.column('target', width = 400, anchor = 'w')
        self.steps_tree.pack(fill = 'both', expand = True, side = 'left')
        steps_sc = ttk.Scrollbar(steps_box, orient = 'vertical', command = self.steps_tree.yview)
        self.steps_tree.configure(yscrollcommand = steps_sc.set)
        steps_sc.pack(side = 'right', fill = 'y')
        step_btns = ttk.Frame(root)
        step_btns.pack(fill = 'x', pady = (8, 0))
        ttk.Button(step_btns, text = '실행추가', command = self._add_step).pack(side = 'left')
        ttk.Button(step_btns, text = '실행편집', command = self._edit_step).pack(side = 'left', padx = 8)
        ttk.Button(step_btns, text = '실행삭제', command = self._delete_step).pack(side = 'left', padx = 8)
        info_text = '예: 시작 키 1 + 실행할 동작 0.5초 우클릭, 0.6초 r키를 등록하면 1번 입력 후 순서대로 실행됩니다.'
        ttk.Label(root, text = info_text).pack(anchor = 'w', pady = (10, 0))
        ttk.Separator(dialog_root, orient = 'horizontal').pack(fill = 'x', pady = (10, 0))
        btns = ttk.Frame(dialog_root)
        btns.pack(fill = 'x', pady = (10, 0))
        ttk.Button(btns, text = '취소', command = self._close).pack(side = 'right')
        ttk.Button(btns, text = '확인', command = self._submit).pack(side = 'right', padx = 8)
        self._sync_state()
        self._refresh_steps_tree()
        self._fit_dialog()

    
    def _fit_dialog(self):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        scroll_content = getattr(self, '_scroll_content', None)
        content_req_h = 0
        if scroll_content is not None:
            
            try:
                content_req_h = scroll_content.winfo_reqheight()
            except Exception:
                content_req_h = 0

            fixed_bottom_h = 78
            win_w = min(max(680, self.winfo_reqwidth() + 20), int(screen_w * 0.9))
            win_h = min(max(640, self.winfo_reqheight() + 20, content_req_h + fixed_bottom_h), int(screen_h * 0.86))
            x = max(0, (screen_w - win_w) // 2)
            y = max(0, (screen_h - win_h) // 2)
            self.geometry(f'''{win_w}x{win_h}+{x}+{y}''')
            self.minsize(min(680, win_w), min(560, win_h))
            return None

    
    def _sync_state(self):
        if self.trigger_type_var.get() == 'key':
            self.trigger_key_entry.configure(state = 'readonly')
            self.trigger_key_button.configure(state = 'normal')
            self.trigger_mouse_left.configure(state = 'disabled')
            self.trigger_mouse_right.configure(state = 'disabled')
            self.trigger_mouse_middle.configure(state = 'disabled')
            self.trigger_mouse_custom_radio.configure(state = 'disabled')
            self.trigger_custom_entry.configure(state = 'disabled')
            self.trigger_custom_button.configure(state = 'disabled')
        else:
            self.trigger_key_entry.configure(state = 'disabled')
            self.trigger_key_button.configure(state = 'disabled')
            self.trigger_mouse_left.configure(state = 'normal')
            self.trigger_mouse_right.configure(state = 'normal')
            self.trigger_mouse_middle.configure(state = 'normal')
            self.trigger_mouse_custom_radio.configure(state = 'normal')
            self.trigger_custom_entry.configure(state = 'readonly')
            self.trigger_custom_button.configure(state = 'normal')
        execution_mode = self.execution_mode_var.get()
        is_repeat = execution_mode == 'repeat'
        is_hold = execution_mode == 'hold_while_pressed'
        if is_hold:
            self.run_mode_var.set('hold_while_pressed')
            self.always_mode_var.set('restart')
        elif self.run_mode_var.get() == 'hold_while_pressed':
            self.run_mode_var.set('skip_while_running')
        if is_repeat and self.always_mode_var.get() == 'append':
            self.always_mode_var.set('restart')
        run_mode_state = 'disabled' if is_hold else 'normal'
        hold_mode_state = 'normal' if is_hold else 'disabled'
        if hasattr(self, 'run_always_radio'):
            self.run_always_radio.configure(state = run_mode_state)
        if hasattr(self, 'run_skip_radio'):
            self.run_skip_radio.configure(state = run_mode_state)
        if hasattr(self, 'run_hold_radio'):
            self.run_hold_radio.configure(state = hold_mode_state)
        always_restart_state = 'normal' if not self.run_mode_var.get() == 'always' and is_hold else 'disabled'
        always_append_state = 'normal' if not self.run_mode_var.get() == 'always' and is_repeat and is_hold else 'disabled'
        if hasattr(self, 'always_restart_radio'):
            self.always_restart_radio.configure(state = always_restart_state)
        if hasattr(self, 'always_append_radio'):
            self.always_append_radio.configure(state = always_append_state)
        repeat_check_state = 'normal' if is_repeat else 'disabled'
        if hasattr(self, 'repeat_include_trigger_check'):
            self.repeat_include_trigger_check.configure(state = repeat_check_state)
        hold_state = 'normal' if is_hold else 'disabled'
        if hasattr(self, 'hold_stop_now_radio'):
            self.hold_stop_now_radio.configure(state = hold_state)
        if hasattr(self, 'hold_stop_finish_radio'):
            self.hold_stop_finish_radio.configure(state = hold_state)
            return None

    
    def _pick_trigger_key(self):
        
        def done(ks = None):
            self.trigger_key_var.set(ks)

        self.master._capture_one_key('발동 키 지정', done)

    
    def _pick_trigger_custom_mouse(self):
        
        def done(value = None):
            self.trigger_custom_mouse_var.set(value)
            self.trigger_mouse_choice_var.set('custom')

        self.master._capture_custom_mouse_button('시작 그외 마우스 버튼추가', done)

    
    def _selected_trigger_mouse_storage(self = None):
        choice = self.trigger_mouse_choice_var.get()
        if choice == 'custom':
            custom_value = self.trigger_custom_mouse_var.get().strip()
            (button_type, button) = mouse_hotkey_storage(custom_value)
            if button_type == 'custom' and button:
                return ('custom', button)
            return ('', '')
        return ('basic', choice)

    
    def _refresh_steps_tree(self):
        for i in self.steps_tree.get_children():
            self.steps_tree.delete(i)
        for step in sorted(self.steps, key = (lambda x: float(x.get('delay', 0.0001)))):
            try:
                delay = parse_interval(str(step.get('delay', 0.0001)))
            except Exception:
                delay = 0.0001
            target_text = self.master._format_trigger_target(step)
            self.steps_tree.insert('', 'end', iid = step['id'], values = (format_interval_value(delay), target_text))
        return None

    
    def _get_selected_step_id(self):
        sel = self.steps_tree.selection()
        if sel:
            return sel[0]

    
    def _add_step(self):
        TriggerStepDialog(self, mode = 'add', initial = None, on_submit = self._append_step)

    
    def _edit_step(self):
        sid = self._get_selected_step_id()
        if not sid:
            messagebox.showinfo('안내', '편집할 실행 항목을 선택하세요.')
            return None
        step = next((x for x in self.steps if x['id'] == sid), None)
        if not step:
            return None
        TriggerStepDialog(self, mode = 'edit', initial = step, on_submit = self._replace_step)

    
    def _delete_step(self):
        sid = self._get_selected_step_id()
        if not sid:
            messagebox.showinfo('안내', '삭제할 실행 항목을 선택하세요.')
            return None
        self.steps = [x for x in self.steps if x['id'] != sid]
        self._refresh_steps_tree()
        return None
        

    
    def _append_step(self = None, step = None):
        clean_step = dict(step)
        clean_step['id'] = clean_step.get('id') or uuid.uuid4().hex
        self.steps.append(clean_step)
        self._refresh_steps_tree()

    
    def _replace_step(self = None, step = None):
        existing = next((i for i, x in enumerate(self.steps) if x['id'] == step['id']), None)
        if existing is None:
            self.steps.append(step)
        else:
            self.steps[existing] = step
        self._refresh_steps_tree()

    
    def _submit(self):
        trigger_type = self.trigger_type_var.get()
        execution_mode = self.execution_mode_var.get()
        reserved_keys = self.master._reserved_hotkeys(include_pause = True)
        if not self.steps:
            messagebox.showwarning('안내', '자동 실행 목록을 1개 이상 추가하세요.')
            return None
        if execution_mode == 'hold_while_pressed':
            run_mode_value = 'skip_while_running'
            always_mode_value = 'restart'
        else:
            run_mode_value = self.run_mode_var.get()
            always_mode_value = 'restart' if execution_mode == 'repeat' and self.always_mode_var.get() == 'append' else self.always_mode_var.get()
        action = {
            'id': self.id_value,
            'trigger_type': trigger_type,
            'execution_mode': execution_mode,
            'hold_stop_mode': self.hold_stop_mode_var.get() if execution_mode == 'hold_while_pressed' else 'stop_immediately',
            'repeat_include_trigger': bool(self.repeat_include_trigger_var.get()) if execution_mode == 'repeat' else False,
            'run_mode': run_mode_value,
            'always_mode': always_mode_value,
            'steps': sorted(self.steps, key = (lambda x: float(x.get('delay', 0.0001)))) }
        if trigger_type == 'key':
            trigger_key = self.trigger_key_var.get().strip()
            if not trigger_key:
                messagebox.showwarning('안내', '시작 키를 지정하세요.')
                return None
            if trigger_key in reserved_keys:
                messagebox.showwarning('안내', '시작 키는 시작키/종료키/일시정지키/빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
                return None
            action['trigger_key'] = trigger_key
            action['trigger_button_type'] = 'basic'
            action['trigger_button'] = ''
        else:
            (trigger_button_type, trigger_button) = self._selected_trigger_mouse_storage()
            if not trigger_button_type or not trigger_button:
                messagebox.showinfo('안내', '그외 버튼추가를 눌러 시작 마우스 버튼을 먼저 등록하세요.')
                return None
            trigger_mouse_hotkey = mouse_button_hotkey(trigger_button, trigger_button_type)
            if trigger_mouse_hotkey in reserved_keys:
                messagebox.showwarning('안내', '시작 마우스는 시작키/종료키/일시정지키/빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
                return None
            action['trigger_key'] = ''
            action['trigger_button_type'] = trigger_button_type
            action['trigger_button'] = trigger_button
        for step in action['steps']:
            if step.get('target_type') == 'key':
                target_key = step.get('target_key', '').strip()
                if not target_key:
                    messagebox.showwarning('안내', '실행 목록에 비어있는 키가 있습니다.')
                    action['steps']
                    return None
                if target_key in reserved_keys:
                    messagebox.showwarning('안내', '실행 키는 시작키/종료키/일시정지키/빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
                    return None
            if step.get('target_type') == 'mouse':
                button_type = normalize_mouse_button_type(step.get('target_button_type'), step.get('target_button', 'left'))
                target_button = step.get('target_button', 'left')
                target_mouse_hotkey = mouse_button_hotkey(target_button, button_type)
                if target_mouse_hotkey in reserved_keys:
                    messagebox.showwarning('안내', '실행 마우스는 시작키/종료키/일시정지키/빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
                    return None
            if not execution_mode in frozenset({'repeat', 'hold_while_pressed'}):
                continue
            if not self.master._same_trigger_and_step(action, step):
                continue
            messagebox.showwarning('안내', "반복실행 또는 누르고 있는 동안 실행에서는 시작키를 실행 목록에 넣을 수 없습니다.\n시작키를 반복마다 같이 실행하려면 반복실행에서 '시작키를 매 반복 첫 동작에 포함'을 선택해주세요.")
            return None
        self.on_submit(action)
        self._close()

    
    def _close(self):
        if not self._input_block_closed:
            self._input_block_closed = True
            self.master._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None




class TriggerStepDialog(tk.Toplevel):
    
    def __init__(self = None, master = None, mode = None, initial = None, on_submit = None):
        super().__init__(master)
        self.parent = master
        self.mode = mode
        self.initial = initial
        self.on_submit = on_submit
        self._input_block_closed = False
        self.parent.master._begin_input_block()
        self.title('실행 추가' if mode == 'add' else '실행 편집')
        self.parent.master._center_child_window(self, 500, 330)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.id_value = initial['id'] if initial else uuid.uuid4().hex
        self.delay_var = tk.StringVar(value = format_interval_value(initial.get('delay', 0.0001)) if initial else '0.0001')
        self.target_type_var = tk.StringVar(value = initial.get('target_type') if initial else 'key')
        self.target_key_var = tk.StringVar(value = initial.get('target_key') if initial else '')
        initial_target_button = initial.get('target_button') if initial else 'left'
        initial_target_button_type = normalize_mouse_button_type(initial.get('target_button_type') if initial else None, initial_target_button)
        self.target_mouse_choice_var = tk.StringVar(value = initial_target_button if initial_target_button_type == 'basic' else 'custom')
        self.target_custom_mouse_var = tk.StringVar(value = mouse_button_hotkey(initial_target_button, 'custom') if initial_target_button_type == 'custom' else '')
        self._build()

    
    def _build(self):
        root = ttk.Frame(self, padding = 12)
        root.pack(fill = 'both', expand = True)
        delay_box = ttk.LabelFrame(root, text = '지연 시간', padding = 10)
        delay_box.pack(fill = 'x')
        delay_row = ttk.Frame(delay_box)
        delay_row.pack(fill = 'x')
        ttk.Entry(delay_row, textvariable = self.delay_var, width = 12, justify = 'center').pack(side = 'left')
        ttk.Label(delay_row, text = '초 후 실행 (0.0001 단위, 예: 0.0001, 0.5, 1.2345)').pack(side = 'left', padx = 10)
        target_box = ttk.LabelFrame(root, text = '자동 실행 대상', padding = 10)
        target_box.pack(fill = 'x', pady = (10, 0))
        target_type_row = ttk.Frame(target_box)
        target_type_row.pack(fill = 'x')
        ttk.Radiobutton(target_type_row, text = '키', value = 'key', variable = self.target_type_var, command = self._sync_state).pack(side = 'left')
        ttk.Radiobutton(target_type_row, text = '마우스', value = 'mouse', variable = self.target_type_var, command = self._sync_state).pack(side = 'left', padx = 14)
        target_key_row = ttk.Frame(target_box)
        target_key_row.pack(fill = 'x', pady = (8, 0))
        ttk.Label(target_key_row, text = '실행 키').pack(side = 'left')
        self.target_key_entry = ttk.Entry(target_key_row, textvariable = self.target_key_var, width = 22, state = 'readonly')
        self.target_key_entry.pack(side = 'left', padx = 8)
        self.target_key_button = ttk.Button(target_key_row, text = '키 지정', command = self._pick_target_key)
        self.target_key_button.pack(side = 'left')
        target_mouse_row = ttk.Frame(target_box)
        target_mouse_row.pack(fill = 'x', pady = (8, 0))
        ttk.Label(target_mouse_row, text = '실행 마우스').pack(side = 'left')
        
        def select_target_basic_mouse():
            self.target_custom_mouse_var.set('')

        self.target_mouse_left = ttk.Radiobutton(target_mouse_row, text = '왼쪽버튼', value = 'left', variable = self.target_mouse_choice_var, command = select_target_basic_mouse)
        self.target_mouse_left.pack(side = 'left', padx = 8)
        self.target_mouse_right = ttk.Radiobutton(target_mouse_row, text = '오른쪽버튼', value = 'right', variable = self.target_mouse_choice_var, command = select_target_basic_mouse)
        self.target_mouse_right.pack(side = 'left', padx = 8)
        self.target_mouse_middle = ttk.Radiobutton(target_mouse_row, text = '휠클릭', value = 'middle', variable = self.target_mouse_choice_var, command = select_target_basic_mouse)
        self.target_mouse_middle.pack(side = 'left', padx = 8)
        target_custom_row = ttk.Frame(target_box)
        target_custom_row.pack(fill = 'x', pady = 2)
        self.target_mouse_custom_radio = ttk.Radiobutton(target_custom_row, text = '그외 버튼', value = 'custom', variable = self.target_mouse_choice_var)
        self.target_mouse_custom_radio.pack(side = 'left')
        self.target_custom_entry = ttk.Entry(target_custom_row, textvariable = self.target_custom_mouse_var, width = 28, state = 'readonly')
        self.target_custom_entry.pack(side = 'left', padx = 8)
        self.target_custom_button = ttk.Button(target_custom_row, text = '그외 버튼추가', command = self._pick_target_custom_mouse)
        self.target_custom_button.pack(side = 'left')
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (14, 0))
        ttk.Button(btns, text = '취소', command = self._close).pack(side = 'right')
        ttk.Button(btns, text = '확인', command = self._submit).pack(side = 'right', padx = 8)
        self._sync_state()

    
    def _sync_state(self):
        if self.target_type_var.get() == 'key':
            self.target_key_entry.configure(state = 'readonly')
            self.target_key_button.configure(state = 'normal')
            self.target_mouse_left.configure(state = 'disabled')
            self.target_mouse_right.configure(state = 'disabled')
            self.target_mouse_middle.configure(state = 'disabled')
            self.target_mouse_custom_radio.configure(state = 'disabled')
            self.target_custom_entry.configure(state = 'disabled')
            self.target_custom_button.configure(state = 'disabled')
            return None
        self.target_key_entry.configure(state = 'disabled')
        self.target_key_button.configure(state = 'disabled')
        self.target_mouse_left.configure(state = 'normal')
        self.target_mouse_right.configure(state = 'normal')
        self.target_mouse_middle.configure(state = 'normal')
        self.target_mouse_custom_radio.configure(state = 'normal')
        self.target_custom_entry.configure(state = 'readonly')
        self.target_custom_button.configure(state = 'normal')

    
    def _pick_target_key(self):
        
        def done(ks = None):
            self.target_key_var.set(ks)

        self.parent.master._capture_one_key('실행 키 지정', done)

    
    def _pick_target_custom_mouse(self):
        
        def done(value = None):
            self.target_custom_mouse_var.set(value)
            self.target_mouse_choice_var.set('custom')

        self.parent.master._capture_custom_mouse_button('실행 그외 마우스 버튼추가', done)

    
    def _selected_target_mouse_storage(self = None):
        choice = self.target_mouse_choice_var.get()
        if choice == 'custom':
            custom_value = self.target_custom_mouse_var.get().strip()
            (button_type, button) = mouse_hotkey_storage(custom_value)
            if button_type == 'custom' and button:
                return ('custom', button)
            return ('', '')
        return ('basic', choice)

    
    def _submit(self):
        
        try:
            delay = parse_interval(self.delay_var.get().strip())
        except Exception:
            messagebox.showwarning('안내', '지연 시간은 숫자로 입력하세요. (최소 0.0001, 소수점 4자리)')
            return None

        target_type = self.target_type_var.get()
        step = {
            'id': self.id_value,
            'delay': delay,
            'target_type': target_type }
        reserved_keys = self.parent.master._reserved_hotkeys(include_pause = True)
        if target_type == 'key':
            target_key = self.target_key_var.get().strip()
            if not target_key:
                messagebox.showwarning('안내', '실행 키를 지정하세요.')
                return None
            if target_key in reserved_keys:
                messagebox.showwarning('안내', '실행 키는 시작키/종료키/일시정지키/빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
                return None
            step['target_key'] = target_key
            step['target_button_type'] = 'basic'
            step['target_button'] = ''
        else:
            (target_button_type, target_button) = self._selected_target_mouse_storage()
            if not target_button_type or not target_button:
                messagebox.showinfo('안내', '그외 버튼추가를 눌러 실행 마우스 버튼을 먼저 등록하세요.')
                return None
            target_mouse_hotkey = mouse_button_hotkey(target_button, target_button_type)
            if target_mouse_hotkey in reserved_keys:
                messagebox.showwarning('안내', '실행 마우스는 시작키/종료키/일시정지키/빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
                return None
            step['target_key'] = ''
            step['target_button_type'] = target_button_type
            step['target_button'] = target_button
        if self.parent.execution_mode_var.get() in frozenset({'repeat', 'hold_while_pressed'}):
            temp_action = {
                'trigger_type': self.parent.trigger_type_var.get() }
            if temp_action['trigger_type'] == 'key':
                temp_action['trigger_key'] = self.parent.trigger_key_var.get().strip()
            else:
                (trigger_button_type, trigger_button) = self.parent._selected_trigger_mouse_storage()
                temp_action['trigger_button_type'] = trigger_button_type
                temp_action['trigger_button'] = trigger_button
            if self.parent.master._same_trigger_and_step(temp_action, step):
                messagebox.showwarning('안내', "반복실행 또는 누르고 있는 동안 실행에서는 시작키를 실행 목록에 넣을 수 없습니다.\n시작키를 반복마다 같이 실행하려면 반복실행에서 '시작키를 매 반복 첫 동작에 포함'을 선택해주세요.")
                return None
        self.on_submit(step)
        self._close()

    
    def _close(self):
        if not self._input_block_closed:
            self._input_block_closed = True
            self.parent.master._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None




class ActionDialog(tk.Toplevel):
    
    def __init__(self = None, master = None, mode = None, action_type = None, initial = None, on_submit = None):
        super().__init__(master)
        self.master = master
        self.mode = mode
        self.action_type = action_type
        self.initial = initial
        self.on_submit = on_submit
        self._input_block_closed = False
        self.master._begin_input_block()
        self.display_title = '반복 키' if action_type == 'key' else '반복 마우스'
        self.title(f'''{self.display_title} 추가''' if mode == 'add' else f'''{self.display_title} 편집''')
        master._center_child_window(self, 500, 390)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.protocol('WM_DELETE_WINDOW', self._close)
        self.id_value = initial['id'] if initial else uuid.uuid4().hex
        self.mode_var = tk.StringVar(value = initial.get('mode') if initial else 'click')
        self.interval_var = tk.StringVar(value = format_interval_value(initial.get('interval', 0.0001)) if initial else '0.0001')
        self.key_str_var = tk.StringVar(value = initial.get('key') if initial else '')
        initial_button = initial.get('button') if initial else 'left'
        initial_button_type = normalize_mouse_button_type(initial.get('button_type') if initial else None, initial_button)
        self.mouse_choice_var = tk.StringVar(value = initial_button if initial_button_type == 'basic' else 'custom')
        self.custom_mouse_var = tk.StringVar(value = mouse_button_hotkey(initial_button, 'custom') if initial_button_type == 'custom' else '')
        self._build()

    
    def _build(self):
        root = ttk.Frame(self, padding = 12)
        root.pack(fill = 'both', expand = True)
        ttk.Label(root, text = self.display_title, font = ('', 12)).pack(anchor = 'w')
        box1 = ttk.LabelFrame(root, text = '대상', padding = 10)
        box1.pack(fill = 'x', pady = (10, 0))
        if self.action_type == 'key':
            row = ttk.Frame(box1)
            row.pack(fill = 'x')
            ttk.Entry(row, textvariable = self.key_str_var, width = 22, state = 'readonly').pack(side = 'left')
            ttk.Button(row, text = '키 지정', command = self._pick_key).pack(side = 'left', padx = 10)
        else:
            row = ttk.Frame(box1)
            row.pack(fill = 'x')
            
            def select_basic_mouse():
                self.custom_mouse_var.set('')

            ttk.Radiobutton(row, text = '왼쪽버튼', value = 'left', variable = self.mouse_choice_var, command = select_basic_mouse).pack(side = 'left')
            ttk.Radiobutton(row, text = '오른쪽버튼', value = 'right', variable = self.mouse_choice_var, command = select_basic_mouse).pack(side = 'left', padx = 14)
            ttk.Radiobutton(row, text = '휠클릭', value = 'middle', variable = self.mouse_choice_var, command = select_basic_mouse).pack(side = 'left', padx = 14)
            custom_row = ttk.Frame(box1)
            custom_row.pack(fill = 'x', pady = 2)
            ttk.Radiobutton(custom_row, text = '그외 버튼', value = 'custom', variable = self.mouse_choice_var).pack(side = 'left')
            ttk.Entry(custom_row, textvariable = self.custom_mouse_var, width = 30, state = 'readonly', justify = 'center').pack(side = 'left', fill = 'x', expand = True, padx = (8, 8))
            ttk.Button(custom_row, text = '그외 버튼추가', command = self._pick_custom_mouse).pack(side = 'left')
        box2 = ttk.LabelFrame(root, text = '동작', padding = 10)
        box2.pack(fill = 'x', pady = (10, 0))
        row2 = ttk.Frame(box2)
        row2.pack(fill = 'x')
        ttk.Radiobutton(row2, text = '클릭(반복)', value = 'click', variable = self.mode_var, command = self._sync_state).pack(side = 'left')
        ttk.Radiobutton(row2, text = '누르기(홀드)', value = 'hold', variable = self.mode_var, command = self._sync_state).pack(side = 'left', padx = 14)
        box3 = ttk.LabelFrame(root, text = '반복 주기(초) - 클릭 선택 시만', padding = 10)
        box3.pack(fill = 'x', pady = (10, 0))
        row3 = ttk.Frame(box3)
        row3.pack(fill = 'x')
        self.interval_entry = ttk.Entry(row3, textvariable = self.interval_var, width = 12, justify = 'center')
        self.interval_entry.pack(side = 'left')
        ttk.Label(row3, text = '0.0001 단위 (예: 0.0001, 0.5, 1.2345)').pack(side = 'left', padx = 10)
        btns = ttk.Frame(root)
        btns.pack(fill = 'x', pady = (14, 0))
        ttk.Button(btns, text = '취소', command = self._close).pack(side = 'right')
        ttk.Button(btns, text = '확인', command = self._submit).pack(side = 'right', padx = 8)
        self._sync_state()

    
    def _sync_state(self):
        if self.mode_var.get() == 'hold':
            self.interval_entry.configure(state = 'disabled')
            return None
        self.interval_entry.configure(state = 'normal')

    
    def _pick_key(self):
        
        def done(ks = None):
            self.key_str_var.set(ks)

        self.master._capture_one_key('키 지정', done)

    
    def _pick_custom_mouse(self):
        
        def done(value = None):
            self.custom_mouse_var.set(value)
            self.mouse_choice_var.set('custom')

        self.master._capture_custom_mouse_button('반복 그외 마우스 버튼추가', done)

    
    def _selected_mouse_storage(self = None):
        choice = self.mouse_choice_var.get()
        if choice == 'custom':
            custom_value = self.custom_mouse_var.get().strip()
            (button_type, button) = mouse_hotkey_storage(custom_value)
            if button_type == 'custom' and button:
                return ('custom', button)
            return ('', '')
        return ('basic', choice)

    
    def _submit(self):
        mode = self.mode_var.get()
        if self.action_type == 'key':
            ks = self.key_str_var.get().strip()
            if not ks:
                messagebox.showwarning('안내', '키를 지정하세요.')
                return None
            target = {
                'key': ks }
        else:
            (button_type, button) = self._selected_mouse_storage()
            if not button_type or not button:
                messagebox.showinfo('안내', '그외 버튼추가를 눌러 마우스 버튼을 먼저 등록하세요.')
                return None
            target_mouse_hotkey = mouse_button_hotkey(button, button_type)
            reserved_keys = self.master._reserved_hotkeys(include_pause = True)
            if target_mouse_hotkey in reserved_keys:
                messagebox.showwarning('안내', '반복 마우스는 시작키/종료키/일시정지키/빨리줍기키/빠른우클릭키와 다르게 설정하세요.')
                return None
            target = {
                'button_type': button_type,
                'button': button }
        action = {
            'id': self.id_value,
            'type': self.action_type,
            'mode': mode }
        action.update(target)
        if mode == 'click':
            
            try:
                action['interval'] = parse_interval(self.interval_var.get().strip())
            except Exception:
                messagebox.showwarning('안내', '반복 주기는 숫자로 입력하세요. (최소 0.0001, 소수점 4자리)')
                return None

        else:
            action['interval'] = 0
        self.on_submit(action)
        self._close()

    
    def _close(self):
        if not self._input_block_closed:
            self._input_block_closed = True
            self.master._end_input_block()
        
        try:
            self.grab_release()
        except Exception:
            pass

        
        try:
            self.destroy()
            return None
        except Exception:
            return None



if __name__ == '__main__':
    app = MacroApp()
    app.mainloop()

