import sys
import psutil
import winreg
import ctypes
import datetime
import calendar
import math
import locale
import qtawesome as qta
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup, QPointF, pyqtProperty, QSize
from PyQt6.QtGui import (QCursor, QPainter, QColor, QBrush, QPaintEvent, 
                         QLinearGradient, QRadialGradient, QConicalGradient, QAction, QPen, QPainterPath, QRegion, QPixmap, QGuiApplication, QFont)
import json
import os
import webbrowser
import subprocess

from app_styles import get_stylesheet
from media_monitor import MediaMonitor
from event_monitor import KeyLockMonitor
from notification_monitor import NotificationMonitor
from weather_monitor import WeatherMonitor
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QMenu, QPushButton, QGraphicsOpacityEffect, 
                             QGridLayout, QFrame, QProgressBar, QInputDialog,
                             QDialog, QLineEdit, QListWidget, QListWidgetItem,
                             QComboBox, QScrollArea, QSlider, QFileDialog, QDateEdit, QSizePolicy)

DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMSBT_DISABLE = 1
DWMWCP_ROUND = 2

DEFAULT_TASKS = [
    {"name": "Sincronizar Proyecto", "category": "Trabajo", "color": "#00A0FF", "time": "14:00", "date": datetime.date.today().strftime("%Y-%m-%d")},
    {"name": "Ir al Gimnasio", "category": "Salud", "color": "#00FF80", "time": "17:30", "date": datetime.date.today().strftime("%Y-%m-%d")},
    {"name": "Cena Familiar", "category": "Personal", "color": "#FF5050", "time": "20:00", "date": datetime.date.today().strftime("%Y-%m-%d")}
]

DEFAULT_APPS = [
    {"name": "YouTube", "icon": "mdi.youtube", "cmd": "https://www.youtube.com"},
    {"name": "Twitch", "icon": "mdi.twitch", "cmd": "https://www.twitch.tv"},
    {"name": "Discord", "icon": "mdi.discord", "cmd": "discord"},
    {"name": "WhatsApp", "icon": "mdi.whatsapp", "cmd": "https://web.whatsapp.com"},
    {"name": "Spotify", "icon": "mdi.spotify", "cmd": "spotify"}
]

SYSTEM_SHORTCUTS = [
    {"name": "Apagar", "icon": "mdi.power", "cmd": "shutdown /s /t 0", "color": "#FF453A"},
    {"name": "Reiniciar", "icon": "mdi.refresh", "cmd": "shutdown /r /t 0", "color": "#FF9F0A"},
    {"name": "Hibernar", "icon": "mdi.snowflake", "cmd": "shutdown /h", "color": "#64D2FF"},
    {"name": "Cerrar Sesión", "icon": "mdi.logout", "cmd": "shutdown /l", "color": "#BF5AF2"},
    {"name": "Configuración", "icon": "mdi.cog-outline", "cmd": "start ms-settings:", "color": "#98989D"},
    {"name": "Cambiar Tema", "icon": "mdi.theme-light-dark", "action": "toggle_theme", "color": "#FFD60A"},
    {"name": "Explorador", "icon": "mdi.folder-outline", "cmd": "explorer .", "color": "#FFD60A"},
]

class ProgressRingWidget(QWidget):
    def __init__(self, title, label_text, percentage, color, parent=None):
        super().__init__(parent)
        self.title = title
        self.label_text = label_text
        self.percentage = percentage
        self.ring_color = color
        self.setFixedSize(160, 150)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(20, 15, 120, 120)
        
        painter.setPen(QPen(QColor(255, 255, 255, 35), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)
        
        span_angle = int(-self.percentage * 360 * 16 / 100)
        painter.setPen(QPen(QColor(self.ring_color), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, 90 * 16, span_angle)
        
        if self.percentage > 0:
            angle_rad = math.radians(90 - (self.percentage * 3.6))
            radius = rect.width() / 2.0
            center_x = rect.center().x()
            center_y = rect.center().y()
            dot_x = center_x + radius * math.cos(angle_rad)
            dot_y = center_y - radius * math.sin(angle_rad)
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("white")))
            painter.drawEllipse(QPointF(dot_x, dot_y), 5.5, 5.5)

        painter.setPen(QColor("white"))
        font_label = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font_label)
        painter.drawText(rect.adjusted(0, -15, 0, 0), Qt.AlignmentFlag.AlignCenter, self.label_text)
        
        font_pct = QFont("Segoe UI", 13, QFont.Weight.Bold)
        painter.setFont(font_pct)
        painter.drawText(rect.adjusted(0, 15, 0, 0), Qt.AlignmentFlag.AlignCenter, f"{self.percentage}%")

class DynamicIsland(QWidget):
    def __init__(self):
        super().__init__()
        
        self.is_dialog_open = False
        self.is_editing_tasks = False
        self.compatibility_mode = False
        self.dragging = False
        self.drag_position = QPoint()
        
        self.accent_color = self.get_windows_accent_color()
        self.album_accent_color = QColor(0, 0, 0)
        self.gradient_phase = 0.0
        self.animation_style = "Burbujas Fluidas"
        self.island_style = "Por Defecto" 
        self.is_locked = False
        self.showing_month_grid = False
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.setObjectName("IslandWidget")
        self.setStyleSheet(get_stylesheet(self.accent_color))
        
        self.last_power_plugged = psutil.sensors_battery().power_plugged if psutil.sensors_battery() else False
        
        self._island_w = 200
        self._island_h = 40
        self.island_w_anim = QPropertyAnimation(self, b"island_w")
        self.island_h_anim = QPropertyAnimation(self, b"island_h")
        
        for anim in [self.island_w_anim, self.island_h_anim]:
            anim.setDuration(700)
            anim.setEasingCurve(QEasingCurve.Type.OutExpo)
            
        self._shine_phase = -1.0
        self.shine_anim = QPropertyAnimation(self, b"shine_phase")
        self.shine_anim.setDuration(1800)
        self.shine_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self._charging_phase = 0.0
        self.charging_anim = QPropertyAnimation(self, b"charging_phase")
        self.charging_anim.setDuration(3000)
        self.charging_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Opacidades de fondos sincronizadas
        for attr in ["weather", "calendar", "month", "pomodoro", "sliders", "clipboard", "search", "apps", "basics"]:
            setattr(self, f"_{attr}_bg_opacity", 0.0)
            anim = QPropertyAnimation(self, f"{attr}_bg_opacity".encode())
            anim.setDuration(1200)
            anim.setEasingCurve(QEasingCurve.Type.InOutSine)
            setattr(self, f"{attr}_bg_anim", anim)

        self.weather_bg_phase = 0.0

        self.SEARCH_W, self.SEARCH_H = 420, 110
        self.APPS_W, self.APPS_H = 440, 120
        self.BASICS_W, self.BASICS_H = 440, 115

        self.POMO_W, self.POMO_H = 340, 155
        self.pomo_mode = "Concentración"
        self.pomo_time_left = 25 * 60
        self.pomo_running = False
        self.pomo_timer = QTimer(self)
        self.pomo_timer.timeout.connect(self.tick_pomodoro)

        self.SLIDERS_W, self.SLIDERS_H = 360, 165
        self.CLIPBOARD_W, self.CLIPBOARD_H = 380, 190

        self.power_timer = QTimer(self)
        self.power_timer.timeout.connect(self.check_power_status)
        self.power_timer.start(2000)

        self.IDLE_W, self.IDLE_H = 200, 40  # Ancho aumentado para el clima
        self.EXP_W, self.EXP_H = 340, 100
        self.MUSIC_W, self.MUSIC_H = 420, 40
        self.NOTIFY_W, self.NOTIFY_H = 380, 40
        self.WEATHER_W, self.WEATHER_H = 360, 160
        self.CALENDAR_W, self.CALENDAR_H = 460, 210
        self.MONTH_W, self.MONTH_H = 460, 210 
        self.EDIT_W, self.EDIT_H = 580, 560
        self.WIDE_W = 1200                                             
        
        self.is_charging = False
        self.current_state = "Idle"
        self.media_state = "Idle"
        self.media_title, self.media_artist = "", ""
        
        # Pestañas limpias
        self.features = ["media", "weather", "calendar", "month", "pomodoro", "sliders", "clipboard", "search", "apps", "basics"]
        self.current_feature_index = 0
        self.showing_lyrics = False
        self.media_lyric_text = ""
        self.LYRIC_W = 640
        
        self.clipboard_history = []
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(1000)
        self._last_clipboard_text = ""

        self.event_title, self.event_text = "", ""
        self.revert_timer = QTimer(self)
        self.revert_timer.setSingleShot(True)
        self.revert_timer.timeout.connect(lambda: self.change_state("Idle"))
        
        self.load_settings()
        self.setup_monitors()
        self.init_ui()
        self.setup_autostart()
        
        self.master_timer = QTimer(self)
        self.master_timer.timeout.connect(self.update_content)
        self.master_timer.start(1000)
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_animation)
        self.anim_timer.start(30)
        
        self.hit_timer = QTimer(self)
        self.hit_timer.timeout.connect(self.check_mouse_position)
        self.hit_timer.start(45)
        
        self.setFixedSize(1200, 700)
        if not self.load_custom_position():
            self.recenter_window()
        
        self.anim_group = QParallelAnimationGroup()
        self.opacity_anim = QPropertyAnimation(self.content_opacity, b"opacity")
        self.opacity_anim.setDuration(850)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        self.content_pos_anim = QPropertyAnimation(self.content_container, b"pos")
        self.content_pos_anim.setDuration(850)
        self.content_pos_anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        
        self.anim_group.addAnimation(self.island_w_anim)
        self.anim_group.addAnimation(self.island_h_anim)
        self.anim_group.addAnimation(self.opacity_anim)
        self.anim_group.addAnimation(self.content_pos_anim)

    def get_windows_accent_color(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM")
            v, _ = winreg.QueryValueEx(key, "ColorizationColor")
            winreg.CloseKey(key)
            return f"#{(v & 0xFFFFFF):06x}"
        except:
            return "#0078D7"

    @pyqtProperty(float)
    def shine_phase(self): return self._shine_phase
    @shine_phase.setter
    def shine_phase(self, val): self._shine_phase = val; self.update()

    @pyqtProperty(float)
    def charging_phase(self): return self._charging_phase
    @charging_phase.setter
    def charging_phase(self, val): self._charging_phase = val; self.update()

    @pyqtProperty(float)
    def weather_bg_opacity(self): return self._weather_bg_opacity
    @weather_bg_opacity.setter
    def weather_bg_opacity(self, val): self._weather_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def calendar_bg_opacity(self): return self._calendar_bg_opacity
    @calendar_bg_opacity.setter
    def calendar_bg_opacity(self, val): self._calendar_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def month_bg_opacity(self): return self._month_bg_opacity
    @month_bg_opacity.setter
    def month_bg_opacity(self, val): self._month_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def pomodoro_bg_opacity(self): return self._pomodoro_bg_opacity
    @pomodoro_bg_opacity.setter
    def pomodoro_bg_opacity(self, val): self._pomodoro_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def sliders_bg_opacity(self): return self._sliders_bg_opacity
    @sliders_bg_opacity.setter
    def sliders_bg_opacity(self, val): self._sliders_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def clipboard_bg_opacity(self): return self._clipboard_bg_opacity
    @clipboard_bg_opacity.setter
    def clipboard_bg_opacity(self, val): self._clipboard_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def search_bg_opacity(self): return self._search_bg_opacity
    @search_bg_opacity.setter
    def search_bg_opacity(self, val): self._search_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def apps_bg_opacity(self): return self._apps_bg_opacity
    @apps_bg_opacity.setter
    def apps_bg_opacity(self, val): self._apps_bg_opacity = val; self.update()

    @pyqtProperty(float)
    def basics_bg_opacity(self): return self._basics_bg_opacity
    @basics_bg_opacity.setter
    def basics_bg_opacity(self, val): self._basics_bg_opacity = val; self.update()

    def load_settings(self):
        base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_path, "config.json")
        try:
            with open(self.config_path, "r") as f:
                self.settings = json.load(f)
        except:
            self.settings = {"location": "Lima, Peru", "lat": -12.0464, "lon": -77.0428, "compatibility_mode": False, "tasks": DEFAULT_TASKS, "custom_apps": DEFAULT_APPS}
        
        if "tasks" not in self.settings:
            self.settings["tasks"] = DEFAULT_TASKS
        if "custom_apps" not in self.settings:
            self.settings["custom_apps"] = DEFAULT_APPS
        
        self.compatibility_mode = self.settings.get("compatibility_mode", False)
        self.island_style = self.settings.get("island_style", "Por Defecto")
        self.animation_style = self.settings.get("animation_style", "Burbujas Fluidas")
        self.is_locked = self.settings.get("is_locked", False)

        # Normalizar valores heredados en inglés → español
        style_map = {"Default": "Por Defecto", "Notch Nook": "Notch Nook", "Liquid Glass": "Liquid Glass"}
        anim_map = {"Fluid Blobs": "Burbujas Fluidas", "Glow Sweep": "Barrido Neón", "Neon Border": "Borde LED"}
        self.island_style = style_map.get(self.island_style, self.island_style)
        self.animation_style = anim_map.get(self.animation_style, self.animation_style)
        
        if hasattr(self, 'weather_monitor'):
            self.weather_monitor.city = self.settings.get("location", "Lima, Peru")
            self.weather_monitor.lat = self.settings.get("lat", -12.0464)
            self.weather_monitor.lon = self.settings.get("lon", -77.0428)
            self.weather_monitor.refresh()

    def save_settings(self):
        self.settings["location"] = self.weather_monitor.city
        self.settings["lat"] = self.weather_monitor.lat
        self.settings["lon"] = self.weather_monitor.lon
        self.settings["compatibility_mode"] = self.compatibility_mode
        self.settings["island_style"] = self.island_style
        self.settings["animation_style"] = self.animation_style
        self.settings["is_locked"] = self.is_locked
        with open(self.config_path, "w") as f:
            json.dump(self.settings, f, indent=4)

    def load_custom_position(self):
        if self.is_locked: return False
        pos_data = self.settings.get("window_pos")
        if pos_data and isinstance(pos_data, list) and len(pos_data) == 2:
            self.move(pos_data[0], pos_data[1])
            return True
        return False

    def save_custom_position(self):
        if not self.is_locked:
            self.settings["window_pos"] = [self.x(), self.y()]
            with open(self.config_path, "w") as f:
                json.dump(self.settings, f, indent=4)

    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if not self.is_locked and event.buttons() & Qt.MouseButton.LeftButton and self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.save_custom_position()
            event.accept()

    def toggle_lock_position(self):
        self.is_locked = not self.is_locked
        self.save_settings()
        if self.is_locked:
            self.recenter_window()
            self.show_notification("Isla", "Fija (Bloqueada)", "La isla está fija en su posición por defecto")
        else:
            self.show_notification("Isla", "Flotante (Libre)", "Ahora puedes arrastrar la isla con el ratón a donde quieras")

    def change_location_dialog(self):
        city, ok = QInputDialog.getText(self, "Cambiar Ubicación", "Ingresa el nombre de la ciudad:", text=self.weather_monitor.city)
        if ok and city:
            success, msg = self.weather_monitor.set_location(city)
            if success:
                self.save_settings()
                self.show_notification("Clima", "Ubicación Actualizada", f"Mostrando clima para {msg}")
            else:
                self.show_notification("Clima", "Error", f"No se pudo encontrar: {city}")

    def get_current_radius(self):
        if self.island_style == "Notch Nook":
            return min(self._island_h / 2.0, 18.0)
        return 18.0

    @pyqtProperty(int)
    def island_w(self): return self._island_w
    @island_w.setter
    def island_w(self, val): 
        self._island_w = val
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())
        self.update()

    @pyqtProperty(int)
    def island_h(self): return self._island_h
    @island_h.setter
    def island_h(self, val): 
        self._island_h = val
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())
        self.update()

    def build_notch_path(self, rect):
        radius = self.get_current_radius()
        scoop = min(radius * 1.4, 25.0)
        path = QPainterPath()
        path.moveTo(rect.left() - scoop, rect.top())
        path.cubicTo(
            rect.left() - scoop * 0.05, rect.top(),
            rect.left(), rect.top() + scoop * 0.05,
            rect.left(), rect.top() + scoop
        )
        path.lineTo(rect.left(), rect.bottom() - radius)
        path.quadTo(rect.left(), rect.bottom(), rect.left() + radius, rect.bottom())
        path.lineTo(rect.right() - radius, rect.bottom())
        path.quadTo(rect.right(), rect.bottom(), rect.right(), rect.bottom() - radius)
        path.lineTo(rect.right(), rect.top() + scoop)
        path.cubicTo(
            rect.right(), rect.top() + scoop * 0.05,
            rect.right() + scoop * 0.05, rect.top(),
            rect.right() + scoop, rect.top()
        )
        path.lineTo(rect.left() - scoop, rect.top())
        path.closeSubpath()
        return path

    def _draw_shape(self, painter, rect, radius):
        if self.island_style == "Notch Nook":
            painter.drawPath(self.build_notch_path(rect))
        else:
            painter.drawRoundedRect(rect, radius, radius)

    def paintEvent(self, a0: QPaintEvent):
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.get_island_rect()
        p_rect = rect.adjusted(1, 1, -1, -1)
        radius = self.get_current_radius()
        is_notch = self.island_style == "Notch Nook"

        if self.charging_phase > 0.0:
            self.paint_charging_ears(painter, rect, radius)
        
        painter.setPen(Qt.PenStyle.NoPen)

        if is_notch:
            notch_path = self.build_notch_path(rect)
            for i in range(5):
                painter.setBrush(QColor(0, 0, 0, 15 - i*3))
                shadow_rect = rect.adjusted(i, 0, -i, -i)
                painter.drawPath(self.build_notch_path(shadow_rect))
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawPath(notch_path)
        else:
            for i in range(5): 
                painter.setBrush(QColor(0, 0, 0, 15 - i*3))
                painter.drawRoundedRect(rect.adjusted(i, i, -i, -i), radius, radius)
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawRoundedRect(rect, radius, radius)

        if self._weather_bg_opacity > 0.0: self.paint_weather_bg(painter, rect, radius)
        if self._calendar_bg_opacity > 0.0: self.paint_calendar_bg(painter, rect, radius)
        if self._month_bg_opacity > 0.0: self.paint_month_bg(painter, rect, radius)
        if self._pomodoro_bg_opacity > 0.0: self.paint_pomo_bg(painter, rect, radius)
        if self._sliders_bg_opacity > 0.0: self.paint_sliders_bg(painter, rect, radius)
        if self._clipboard_bg_opacity > 0.0: self.paint_clipboard_bg(painter, rect, radius)
        if self._search_bg_opacity > 0.0: self.paint_custom_bg(painter, rect, radius, self._search_bg_opacity, QColor(20, 60, 40), QColor(0, 150, 100))
        if self._apps_bg_opacity > 0.0: self.paint_custom_bg(painter, rect, radius, self._apps_bg_opacity, QColor(40, 20, 60), QColor(150, 0, 150))
        if self._basics_bg_opacity > 0.0: self.paint_custom_bg(painter, rect, radius, self._basics_bg_opacity, QColor(30, 30, 40), QColor(60, 60, 80))
            
        clip_path = QPainterPath()
        if is_notch:
            clip_path = self.build_notch_path(rect)
        else:
            clip_path.addRoundedRect(QRectF(rect), radius, radius)
        painter.setClipPath(clip_path)

        can_anim = (self.current_state in ("Hover", "Notify") and self.features[self.current_feature_index] == "media") or\
                   (self.current_state == "Idle" and self.features[self.current_feature_index] == "media" and self.media_state in ("Playing", "Paused"))
        
        if can_anim:
            if self.animation_style == "Barrido Neón": self.paint_glow_sweep(painter, rect, radius)
            elif self.animation_style == "Burbujas Fluidas": self.paint_fluid_blobs(painter, rect, radius)
            elif self.animation_style == "Borde LED": self.paint_neon_border(painter, rect, radius)
        else:
            if not is_notch:
                painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor(255, 255, 255, 30), 1.2))
                painter.drawRoundedRect(p_rect, radius, radius)

        if self.shine_phase > 0.0 and self.shine_phase < 1.0:
            self.paint_shine_sweep(painter, rect, radius)
        
        painter.setClipping(False)                   

    def paint_custom_bg(self, painter, rect, radius, opacity, c1, c2):
        painter.save()
        painter.setOpacity(opacity)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, c1); grad.setColorAt(1, c2)
        painter.setBrush(grad); self._draw_shape(painter, rect, radius)
        painter.restore()

    def paint_weather_bg(self, painter, rect, radius):
        painter.save(); painter.setOpacity(self._weather_bg_opacity)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(20, 40, 100)); grad.setColorAt(1, QColor(10, 20, 60))
        painter.setBrush(grad); self._draw_shape(painter, rect, radius); painter.restore()

    def paint_calendar_bg(self, painter, rect, radius):
        painter.save(); painter.setOpacity(self._calendar_bg_opacity)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(60, 40, 0)); grad.setColorAt(1, QColor(30, 20, 0))
        painter.setBrush(grad); self._draw_shape(painter, rect, radius); painter.restore()

    def paint_month_bg(self, painter, rect, radius):
        painter.save(); painter.setOpacity(self._month_bg_opacity)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(30, 0, 50)); grad.setColorAt(1, QColor(15, 0, 30))
        painter.setBrush(grad); self._draw_shape(painter, rect, radius); painter.restore()

    def paint_pomo_bg(self, painter, rect, radius):
        painter.save(); painter.setOpacity(self._pomodoro_bg_opacity)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(70, 15, 20)); grad.setColorAt(1, QColor(35, 5, 10))
        painter.setBrush(grad); self._draw_shape(painter, rect, radius); painter.restore()

    def paint_sliders_bg(self, painter, rect, radius):
        painter.save(); painter.setOpacity(self._sliders_bg_opacity)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(10, 45, 55)); grad.setColorAt(1, QColor(5, 20, 30))
        painter.setBrush(grad); self._draw_shape(painter, rect, radius); painter.restore()

    def paint_clipboard_bg(self, painter, rect, radius):
        painter.save(); painter.setOpacity(self._clipboard_bg_opacity)
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(10, 50, 40)); grad.setColorAt(1, QColor(5, 25, 20))
        painter.setBrush(grad); self._draw_shape(painter, rect, radius); painter.restore()

    def paint_shine_sweep(self, painter, rect, radius):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        p = self.shine_phase
        if p <= 0 or p >= 1.0: return
        start_x = 35; max_reach = rect.width() * 1.5; current_expansion = max_reach * p
        base_alpha = int(220 * math.sin(p * math.pi))
        for i in range(2):
            W = current_expansion * (0.6 + i * 0.1); h = rect.height()
            target_x = start_x + (current_expansion * 0.4); target_y = (h / 2)
            painter.save(); painter.translate(target_x, target_y); painter.scale(2.5, 0.8) 
            grad = QRadialGradient(QPointF(0, 0), W / 2)
            alpha = int(base_alpha * (1.0 - i * 0.3))
            grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            grad.setColorAt(0.3, QColor(0, 160, 255, int(alpha * 0.6)))
            grad.setColorAt(0.6, QColor(90, 0, 255, int(alpha * 0.15)))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(grad); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), W / 2, W / 2)
            painter.restore()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def paint_glow_sweep(self, painter, rect, radius):
        from PyQt6.QtGui import QTransform
        glow = QColor(self.album_accent_color); glow.setAlpha(120)
        gradient = QLinearGradient(0, 0, rect.width(), 0); gradient.setSpread(QLinearGradient.Spread.RepeatSpread)
        gradient.setColorAt(0.0, Qt.GlobalColor.transparent); gradient.setColorAt(0.5, glow); gradient.setColorAt(1.0, Qt.GlobalColor.transparent)
        brush = QBrush(gradient); transform = QTransform(); transform.translate(self.gradient_phase * rect.width() * 2, 0); brush.setTransform(transform)
        painter.setBrush(brush); self._draw_shape(painter, rect, radius)

    def paint_fluid_blobs(self, painter, rect, radius):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        glow_color = QColor(self.album_accent_color); glow_color.setAlpha(100); p = self.gradient_phase * 2 * math.pi
        x1, y1 = rect.width() * (0.2 + 0.15 * math.sin(p)), rect.height() * (0.5 + 0.25 * math.cos(p))
        g1 = QRadialGradient(x1, y1, rect.width() * 0.45); g1.setColorAt(0, glow_color); g1.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g1); self._draw_shape(painter, rect, radius)
        x2, y2 = rect.width() * (0.8 + 0.15 * math.cos(p * 0.7)), rect.height() * (0.5 + 0.25 * math.sin(p * 1.2))
        g2 = QRadialGradient(x2, y2, rect.width() * 0.35); g2.setColorAt(0, QColor(glow_color).lighter(125)); g2.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g2); self._draw_shape(painter, rect, radius)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def paint_neon_border(self, painter, rect, radius):
        conical = QConicalGradient(QPointF(rect.center()), self.gradient_phase * 360)
        for i, c in enumerate(["#F00", "#FF0", "#0F0", "#0FF", "#00F", "#F0F", "#F00"]): conical.setColorAt(i/6.0, QColor(c))
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QBrush(conical), 2.2))
        if self.island_style == "Notch Nook":
            border = QPainterPath()
            r = radius; sc = min(r * 1.4, 25.0); pr = rect.adjusted(1,1,-1,-1)
            border.moveTo(pr.left() - sc, pr.top())
            border.cubicTo(pr.left() - sc * 0.05, pr.top(), pr.left(), pr.top() + sc * 0.05, pr.left(), pr.top() + sc)
            border.lineTo(pr.left(), pr.bottom() - r)
            border.quadTo(pr.left(), pr.bottom(), pr.left() + r, pr.bottom())
            border.lineTo(pr.right() - r, pr.bottom())
            border.quadTo(pr.right(), pr.bottom(), pr.right(), pr.bottom() - r)
            border.lineTo(pr.right(), pr.top() + sc)
            border.cubicTo(pr.right(), pr.top() + sc * 0.05, pr.right() + sc * 0.05, pr.top(), pr.right() + sc, pr.top())
            painter.drawPath(border)
        else:
            painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), radius, radius)

    def update_animation(self):
        self.gradient_phase = (self.gradient_phase + 0.005) % 1.0
        self.weather_bg_phase = (self.weather_bg_phase + 0.003) % 1.0
        if self.current_state in ("Hover", "Notify") or self.media_state in ("Playing", "Paused") or\
           any(getattr(self, f"_{f}_bg_opacity", 0.0) > 0.0 for f in ["weather", "calendar", "month", "pomodoro", "sliders", "clipboard", "search", "apps", "basics"]): 
            self.update()

    def setup_autostart(self):
        try:
            app_path = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{sys.argv[0]}"'
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DynamicIsland", 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
        except Exception as e: print("Autostart error:", e)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self); self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        self.island_root = QWidget(self)
        self.island_root.setObjectName("IslandRoot")
        self.island_root_layout = QVBoxLayout(self.island_root); self.island_root_layout.setContentsMargins(5, 0, 5, 0); self.island_root_layout.setSpacing(0)
        self.content_container = QWidget(); self.content_layout = QVBoxLayout(self.content_container); self.content_layout.setContentsMargins(0, 0, 0, 0); self.content_layout.setSpacing(0)
        self.content_opacity = QGraphicsOpacityEffect(self.content_container); self.content_container.setGraphicsEffect(self.content_opacity)
        
        self.header_widget = QWidget()
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(15, 0, 15, 0)
        self.header_layout.setSpacing(8)

        self.status_icon = QLabel(); self.status_icon.setObjectName("IconLabel"); self.status_icon.setFixedSize(22, 22)
        self.status_icon.setPixmap(qta.icon('mdi.circle', color=self.accent_color).pixmap(20, 20))
        self.status_text = QLabel(""); self.status_text.setObjectName("TitleLabel")
        
        # Widget de Clima a la derecha
        self.island_weather_widget = QWidget()
        self.island_weather_layout = QHBoxLayout(self.island_weather_widget)
        self.island_weather_layout.setContentsMargins(0, 0, 0, 0)
        self.island_weather_layout.setSpacing(6)
        
        self.weather_sep = QLabel("|")
        self.weather_sep.setStyleSheet("color: rgba(255,255,255,50); font-size: 14px; font-weight: 300;")
        self.weather_icon_lbl = QLabel()
        self.weather_icon_lbl.setPixmap(qta.icon('mdi.weather-sunny', color='#FFD60A').pixmap(16, 16))
        self.weather_temp_lbl = QLabel("--°")
        self.weather_temp_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: white;")
        
        self.island_weather_layout.addWidget(self.weather_sep)
        self.island_weather_layout.addWidget(self.weather_icon_lbl)
        self.island_weather_layout.addWidget(self.weather_temp_lbl)

        # ESTIRAMIENTO A LOS LADOS PARA CENTRAR EL TEXTO
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.status_icon)
        self.header_layout.addWidget(self.status_text)
        self.header_layout.addStretch()
        self.header_layout.addWidget(self.island_weather_widget)

        self.media_controls = QWidget(); self.media_controls_layout = QHBoxLayout(self.media_controls); self.media_controls_layout.setContentsMargins(0, 0, 0, 0); self.media_controls_layout.setSpacing(2)
        self.btn_prev = QPushButton(icon=qta.icon('mdi.skip-previous', color='white')); self.btn_play = QPushButton(icon=qta.icon('mdi.play', color='white')); self.btn_next = QPushButton(icon=qta.icon('mdi.skip-next', color='white'))
        for b in [self.btn_prev, self.btn_play, self.btn_next]: b.setObjectName("MediaButton")
        self.btn_prev.clicked.connect(self.media_monitor.prev_track); self.btn_play.clicked.connect(self.media_monitor.toggle_play_pause); self.btn_next.clicked.connect(self.media_monitor.next_track)
        for b in [self.btn_prev, self.btn_play, self.btn_next]: self.media_controls_layout.addWidget(b)
        self.header_layout.addWidget(self.media_controls)
        self.media_controls.hide()
        self.island_weather_widget.hide() # Oculto por defecto en otros estados
        
        self.weather_panel = self.create_weather_panel()
        self.calendar_panel = self.create_calendar_panel()
        self.month_panel = self.create_month_panel()
        self.pomo_panel = self.create_pomodoro_panel()
        self.sliders_panel = self.create_sliders_panel()
        self.clipboard_panel = self.create_clipboard_panel()
        self.search_panel = self.create_search_panel()
        self.apps_panel = self.create_apps_panel()
        self.basics_panel = self.create_basics_panel()
        
        for p in [self.weather_panel, self.calendar_panel, self.month_panel, self.pomo_panel, self.sliders_panel, self.clipboard_panel, self.search_panel, self.apps_panel, self.basics_panel]: p.hide()
        
        self.content_layout.addWidget(self.header_widget)
        self.content_layout.addWidget(self.weather_panel)
        self.content_layout.addWidget(self.calendar_panel)
        self.content_layout.addWidget(self.month_panel)
        self.content_layout.addWidget(self.pomo_panel)
        self.content_layout.addWidget(self.sliders_panel)
        self.content_layout.addWidget(self.clipboard_panel)
        self.content_layout.addWidget(self.search_panel)
        self.content_layout.addWidget(self.apps_panel)
        self.content_layout.addWidget(self.basics_panel)
        
        self.island_root_layout.addWidget(self.content_container); self.update_content()
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())

    def setup_monitors(self):
        self.media_monitor = MediaMonitor(self); self.media_monitor.media_updated.connect(self.update_media); self.media_monitor.start()
        self.media_monitor.lyrics_updated.connect(self.update_lyrics)
        self.key_monitor = KeyLockMonitor(self); self.key_monitor.lock_changed.connect(self.show_key_event); self.key_monitor.start()
        self.notif_monitor = NotificationMonitor(self); self.notif_monitor.notification_received.connect(self.show_notification); self.notif_monitor.start()
        
        loc = self.settings.get("location", "Lima, Peru")
        lat = self.settings.get("lat", -12.0464)
        lon = self.settings.get("lon", -77.0428)
        self.weather_monitor = WeatherMonitor(city=loc, lat=lat, lon=lon)
        self.weather_monitor.weather_updated.connect(self.update_weather)
        self.weather_monitor.start()

    def update_island_geometry(self, rect, radius):
        if not hasattr(self, 'island_root'): return
        self.island_root.setGeometry(int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()))
        path = QPainterPath()
        if self.island_style == "Notch Nook":
            path.moveTo(0, 0)
            path.lineTo(rect.width(), 0)
            path.lineTo(rect.width(), rect.height() - radius)
            path.quadTo(rect.width(), rect.height(), rect.width() - radius, rect.height())
            path.lineTo(radius, rect.height())
            path.quadTo(0, rect.height(), 0, rect.height() - radius)
            path.closeSubpath()
        else:
            path.addRoundedRect(QRectF(0, 0, rect.width(), rect.height()), radius, radius)
        self.island_root.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def paint_charging_ears(self, painter, rect, radius):
        p = self.charging_phase
        if p <= 0: return
        opacity = math.sin(p * math.pi)
        centerY = rect.top() + rect.height() / 2
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        glow_path = QPainterPath()
        glow_path.addRoundedRect(rect.adjusted(-20*opacity, -10*opacity, 20*opacity, 10*opacity), radius+10, radius+10)
        for i in range(3):
            color = QColor(0, 255, 255, int(70 * opacity / (i + 1)))
            painter.setPen(QPen(color, 12 + i*8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPath(glow_path)
        painter.restore()

    def check_power_status(self):
        try:
            battery = psutil.sensors_battery()
            if battery:
                if battery.power_plugged and not self.last_power_plugged:
                    self.trigger_charging_anim()
                self.last_power_plugged = battery.power_plugged
        except: pass

    def trigger_charging_anim(self):
        self.is_charging = True
        self.execute_liquid_transition()
        self.charging_anim.stop()
        self.charging_anim.setStartValue(0.0)
        self.charging_anim.setEndValue(1.0)
        self.charging_anim.start()
        QTimer.singleShot(3100, lambda: setattr(self, 'is_charging', False) or setattr(self, 'charging_phase', 0.0) or self.execute_liquid_transition())

    def show_key_event(self, name, is_on):
        self.event_title = name; self.event_text = ("ACTIVADO" if is_on else "DESACTIVADO")
        if self.current_state == "Notify": self.update_feature_view(); self.execute_liquid_transition()
        else: self.change_state("Notify")
        self.revert_timer.start(2500)

    def show_notification(self, app, title, text):
        self.event_title = app; self.event_text = (f"{title}: {text}" if title else text)
        if self.current_state == "Notify": self.update_feature_view(); self.execute_liquid_transition()
        else: self.change_state("Notify")
        self.revert_timer.start(3500)

    def create_action_button(self, app_type):
        btn = QPushButton(icon=qta.icon('mdi.open-in-new', color='white'))
        btn.setObjectName("ActionButton")
        btn.setFixedSize(32, 32)
        btn.clicked.connect(lambda: self.open_app(app_type))
        return btn

    def open_app(self, app_type):
        schemes = {
            "weather": "bingweather:", 
            "month": "ms-settings:dateandtime",
            "calendar": "https://calendar.google.com"
        }
        if app_type in schemes: 
            webbrowser.open(schemes[app_type])

    def create_search_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(25, 12, 25, 15); l.setSpacing(10)
        header = QHBoxLayout()
        google_icon = QLabel()
        google_icon.setPixmap(qta.icon("mdi.google", color="#4285F4").pixmap(20, 20))
        title = QLabel("Búsqueda Rápida de Google"); title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(google_icon); header.addWidget(title); header.addStretch(); header.addWidget(self.create_action_button("search"))
        l.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escribe y presiona Enter para buscar...")
        self.search_input.setStyleSheet("background-color: rgba(255, 255, 255, 15); border: 1px solid rgba(255, 255, 255, 25); border-radius: 8px; color: white; padding: 8px 12px; font-size: 13px;")
        self.search_input.returnPressed.connect(self.execute_quick_search)
        l.addWidget(self.search_input)
        return w

    def execute_quick_search(self):
        query = self.search_input.text()
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            self.search_input.clear()
            self.show_notification("Búsqueda", "Google", f"Buscando: {query}")

    def create_apps_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(20, 10, 20, 15); l.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel("Aplicaciones Frecuentes"); title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        add_app_btn = QPushButton(icon=qta.icon("mdi.plus", color="white"))
        add_app_btn.setObjectName("ActionButton"); add_app_btn.setFixedSize(28, 28)
        add_app_btn.setToolTip("Añadir aplicación (.exe)")
        add_app_btn.clicked.connect(self.add_custom_application)

        header.addWidget(title); header.addStretch(); header.addWidget(add_app_btn)
        l.addLayout(header)

        self.apps_scroll_layout = QHBoxLayout()
        self.apps_scroll_layout.setSpacing(12)
        self.apps_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.refresh_apps_dock()
        l.addLayout(self.apps_scroll_layout)
        return w

    def refresh_apps_dock(self):
        while self.apps_scroll_layout.count():
            item = self.apps_scroll_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        apps = self.settings.get("custom_apps", DEFAULT_APPS)
        for idx, app in enumerate(apps):
            btn = QPushButton(icon=qta.icon(app.get("icon", "mdi.application"), color="white"))
            btn.setFixedSize(45, 45)
            btn.setToolTip(f"{app['name']}" + (" (Clic derecho para eliminar)" if idx >= 5 else ""))
            btn.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 12); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 20); } QPushButton:hover { background-color: rgba(0, 160, 255, 180); border: 1px solid white; }")
            
            cmd = app["cmd"]
            btn.clicked.connect(lambda _, c=cmd: webbrowser.open(c) if c.startswith("http") else subprocess.Popen(c, shell=True))
            
            if idx >= 5:
                btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                btn.customContextMenuRequested.connect(lambda pos, i=idx: self.remove_custom_application(i))

            self.apps_scroll_layout.addWidget(btn)

    def remove_custom_application(self, index):
        custom_apps = self.settings.get("custom_apps", DEFAULT_APPS)
        if 0 <= index < len(custom_apps):
            removed = custom_apps.pop(index)
            self.settings["custom_apps"] = custom_apps
            self.save_settings()
            self.refresh_apps_dock()
            self.show_notification("Aplicaciones", "Eliminada", f"{removed['name']} fue removida del Dock")

    def add_custom_application(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar Aplicación", "C:/", "Ejecutables (*.exe);;Todos los archivos (*.*)")
        if file_path:
            app_name = os.path.basename(file_path).replace(".exe", "")
            custom_apps = self.settings.get("custom_apps", DEFAULT_APPS)
            custom_apps.append({"name": app_name, "icon": "mdi.gamepad-variant" if "steam" in file_path.lower() else "mdi.application", "cmd": f'"{file_path}"'})
            self.settings["custom_apps"] = custom_apps
            self.save_settings()
            self.refresh_apps_dock()
            self.show_notification("Aplicaciones", "Añadida", f"{app_name} agregada al Dock")

    def create_weather_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(25, 10, 25, 15); l.setSpacing(12)
        h1 = QHBoxLayout(); self.weather_temp_label = QLabel("--°"); self.weather_temp_label.setStyleSheet("font-size: 38px; font-weight: bold;")
        info = QVBoxLayout(); 
        loc_name = self.settings.get("location", "Lima, Peru")
        self.weather_city_label = QLabel(loc_name); self.weather_city_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.weather_cond_label = QLabel("Cargando..."); self.weather_cond_label.setStyleSheet("font-size: 11px; color: #AAA;")
        info.addWidget(self.weather_city_label); info.addWidget(self.weather_cond_label); h1.addLayout(info); h1.addStretch(); h1.addWidget(self.weather_temp_label)
        l.addLayout(h1)
        self.hourly_layout = QHBoxLayout(); self.hourly_layout.setSpacing(5)
                           
        self.hourly_slots = []
        for _ in range(5):
            slot = QVBoxLayout(); slot.setSpacing(2); st = QLabel("--"); st.setStyleSheet("font-size: 9px; color: #888;"); st.setAlignment(Qt.AlignmentFlag.AlignCenter)
            si = QLabel(); si.setPixmap(qta.icon("mdi.weather-cloudy", color='white').pixmap(18, 18)); si.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stp = QLabel("--°"); stp.setStyleSheet("font-size: 10px; font-weight: 600;"); stp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot.addWidget(st); slot.addWidget(si); slot.addWidget(stp); self.hourly_layout.addLayout(slot)
            self.hourly_slots.append((st, si, stp))
        l.addLayout(self.hourly_layout); return w

    def update_weather(self, data):
        self.weather_temp_label.setText(data["temp"])
        self.weather_city_label.setText(data["city"])
        self.weather_cond_label.setText(data["desc"].capitalize())
        
        # Actualizar widget de la isla
        self.weather_temp_lbl.setText(data["temp"])
        self.weather_icon_lbl.setPixmap(qta.icon(data["icon"], color='#FFD60A').pixmap(16, 16))

        for i, slot in enumerate(data["hourly"]):
            if i < len(self.hourly_slots):
                st, si, stp = self.hourly_slots[i]
                st.setText(slot["time"])
                si.setPixmap(qta.icon(slot["icon"], color='white').pixmap(18, 18))
                stp.setText(slot["temp"])

    def create_calendar_panel(self):
        self.calendar_panel_widget = QWidget()
        self.calendar_panel_widget.setFixedSize(self.CALENDAR_W, self.CALENDAR_H)
        cal_layout = QVBoxLayout(self.calendar_panel_widget)
        cal_layout.setContentsMargins(0, 0, 0, 0); cal_layout.setSpacing(0)
        
        self.task_view_widget = QWidget()
        view_layout = QVBoxLayout(self.task_view_widget)
        view_layout.setContentsMargins(25, 12, 25, 18); view_layout.setSpacing(12)
        
        h = QHBoxLayout(); t = QLabel("Google Calendar (Hoy)"); t.setStyleSheet("font-weight: bold; font-size: 15px;")
        self.ev_count_label = QLabel("0 tareas"); self.ev_count_label.setStyleSheet("color: #888; font-size: 11px;")
        
        web_btn = self.create_action_button("calendar")
        web_btn.setToolTip("Abrir Google Calendar")
        
        eb = QPushButton(icon=qta.icon("mdi.pencil", color="white"))
        eb.setObjectName("ActionButton"); eb.setFixedSize(32, 32)
        eb.clicked.connect(self.open_task_editor)
        eb.setToolTip("Gestionar tareas por fecha")

        h.addWidget(web_btn); h.addSpacing(4); h.addWidget(eb); h.addSpacing(5); h.addWidget(t); h.addWidget(self.ev_count_label); h.addStretch()
        view_layout.addLayout(h)
        
        self.tasks_container_widget = QWidget()
        self.tasks_container_layout = QVBoxLayout(self.tasks_container_widget)
        self.tasks_container_layout.setContentsMargins(0, 0, 0, 0); self.tasks_container_layout.setSpacing(10)
        view_layout.addWidget(self.tasks_container_widget); view_layout.addStretch()
        
        self.task_edit_widget = QWidget(); self.task_edit_widget.hide()
        edit_layout = QVBoxLayout(self.task_edit_widget)
        edit_layout.setContentsMargins(20, 15, 20, 15); edit_layout.setSpacing(10)
        
        self.edit_list = QListWidget()
        self.edit_list.setStyleSheet(f"QListWidget {{ background: transparent; border: none; }} QListWidget::item {{ background: rgba(255,255,255,10); border-radius: 8px; padding: 8px; margin-bottom: 4px; color: white; }} QListWidget::item:selected {{ border: 1px solid {self.accent_color}; }}")
        
        input_grid = QGridLayout(); input_grid.setSpacing(8)
        input_style = f"QLineEdit, QComboBox, QDateEdit {{ background-color: rgba(255, 255, 255, 12); border: 1px solid rgba(255, 255, 255, 15); border-radius: 8px; color: white; padding: 8px; font-size: 12px; }} QLineEdit:focus {{ border: 1px solid {self.accent_color}; }}"
        
        self.edit_name = QLineEdit(); self.edit_name.setPlaceholderText("Nombre de la actividad"); self.edit_name.setStyleSheet(input_style)
        self.edit_time = QLineEdit(); self.edit_time.setPlaceholderText("Hora (ej. 16:00)"); self.edit_time.setStyleSheet(input_style)
        
        self.edit_date = QDateEdit()
        self.edit_date.setDate(datetime.date.today())
        self.edit_date.setCalendarPopup(True)
        self.edit_date.setStyleSheet(input_style)

        self.edit_cat = QComboBox(); self.edit_cat.addItems(["Trabajo", "Salud", "Personal", "Estudios", "Otro"]); self.edit_cat.setStyleSheet(input_style)
        
        input_grid.addWidget(self.edit_name, 0, 0, 1, 2)
        input_grid.addWidget(self.edit_date, 1, 0)
        input_grid.addWidget(self.edit_time, 1, 1)
        input_grid.addWidget(self.edit_cat, 2, 0, 1, 2)
        
        btn_style = "QPushButton { background-color: rgba(255, 255, 255, 10); color: white; border: 1px solid rgba(255, 255, 255, 15); border-radius: 8px; padding: 8px; font-weight: 600; } QPushButton:hover { background-color: rgba(255, 255, 255, 20); }"
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Añadir Actividad"); add_btn.clicked.connect(self.add_task_integrated); add_btn.setStyleSheet(btn_style)
        del_btn = QPushButton("Eliminar Seleccionada"); del_btn.clicked.connect(self.delete_task_integrated); del_btn.setStyleSheet(btn_style)
        
        save_btn = QPushButton("Guardar y Ver Actividades de Hoy")
        save_btn.setStyleSheet(f"background-color: {self.accent_color}; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self.save_and_close_editor)
        
        btn_layout.addWidget(add_btn); btn_layout.addWidget(del_btn)
        
        edit_layout.addWidget(QLabel("Gestión de Agenda y Calendario", styleSheet="font-weight: bold; font-size: 15px;"))
        edit_layout.addWidget(self.edit_list)
        edit_layout.addLayout(input_grid)
        edit_layout.addLayout(btn_layout)
        edit_layout.addWidget(save_btn)
        
        cal_layout.addWidget(self.task_view_widget)
        cal_layout.addWidget(self.task_edit_widget)
        
        self.refresh_calendar_panel()
        return self.calendar_panel_widget

    def add_task_integrated(self):
        name = self.edit_name.text()
        task_date = self.edit_date.date().toString("YYYY-MM-DD")
        if name:
            tasks = self.settings.get("tasks", DEFAULT_TASKS)
            tasks.append({
                "name": name, 
                "category": self.edit_cat.currentText(), 
                "time": self.edit_time.text() or "N/A", 
                "date": task_date, 
                "color": "#00A0FF"
            })
            self.settings["tasks"] = tasks
            self.refresh_calendar_panel(); self.edit_name.clear(); self.edit_time.clear()

    def delete_task_integrated(self):
        idx = self.edit_list.currentRow()
        if idx >= 0:
            tasks = self.settings.get("tasks", DEFAULT_TASKS)
            tasks.pop(idx)
            self.settings["tasks"] = tasks
            self.refresh_calendar_panel()

    def save_and_close_editor(self):
        self.save_settings()
        self.open_task_editor()

    def open_task_editor(self):
        self.is_editing_tasks = not self.is_editing_tasks
        self.task_view_widget.setVisible(not self.is_editing_tasks)
        self.task_edit_widget.setVisible(self.is_editing_tasks)
        
        if self.is_editing_tasks:
            self.calendar_panel_widget.setFixedSize(self.EDIT_W, self.EDIT_H)
        else:
            self.calendar_panel_widget.setFixedSize(self.CALENDAR_W, self.CALENDAR_H)
            
        self.compatibility_mode = True if self.is_editing_tasks else getattr(self, "_prev_comp", self.compatibility_mode)
        if self.is_editing_tasks:
            self._prev_comp = self.compatibility_mode
            
        self.recenter_window()
        self.execute_liquid_transition()

    def refresh_calendar_panel(self):
        for child in self.tasks_container_widget.findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
            
        while self.tasks_container_layout.count():
            item = self.tasks_container_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    si = item.layout().takeAt(0)
                    if si.widget(): si.widget().deleteLater()
            
        tasks = self.settings.get("tasks", DEFAULT_TASKS)
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        today_tasks = [t for t in tasks if t.get("date", today_str) == today_str]
        self.ev_count_label.setText(f"{len(today_tasks)} para hoy")
        
        self.edit_list.clear()
        for t in tasks:
            t_date = t.get("date", today_str)
            t_cat = t.get("category", "Tarea").upper()
            item_text = f"[{t_date}] {t['name']} • {t['time']}\n{t_cat}"
            self.edit_list.addItem(QListWidgetItem(item_text))
        
        shown_count = 0
        for t in today_tasks[:3]:
            shown_count += 1
            row = QHBoxLayout()
            bar = QFrame(); bar.setFixedWidth(3); bar.setStyleSheet(f"background-color: {t.get('color', '#00A0FF')}; border-radius: 1px;")
            det = QVBoxLayout(); det.setContentsMargins(0, 0, 0, 0); det.setSpacing(1)
            n = QLabel(t['name']); n.setStyleSheet("font-size: 13px; font-weight: 600; padding: 0px;")
            c = QLabel(t.get('category', 'Tarea')); c.setStyleSheet("font-size: 10px; color: #888; padding: 0px;")
            det.addWidget(n); det.addWidget(c)
            tm = QLabel(t.get('time', '')); tm.setStyleSheet("font-size: 11px; font-weight: 500;")
            row.addWidget(bar); row.addLayout(det); row.addStretch(); row.addWidget(tm)
            self.tasks_container_layout.addLayout(row)
            
        self.CALENDAR_H = 80 + (shown_count * 35)
        if shown_count == 0: self.CALENDAR_H = 105
        
        if not self.is_editing_tasks:
            self.calendar_panel_widget.setFixedSize(self.CALENDAR_W, self.CALENDAR_H)
            if self.current_state == "Hover" and self.features[self.current_feature_index] == "calendar":
                self.execute_liquid_transition()

    def create_month_panel(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(25, 8, 25, 12)
        l.setSpacing(6)

        now = datetime.datetime.now()
        meses_abrev = ["Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Sep.", "Oct.", "Nov.", "Dic."]
        dias_sem = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        # 1. Mes abreviado con día (ej. "Oct. 26") y día de semana
        label_mes_texto = f"{meses_abrev[now.month - 1]} {now.day}"
        label_dia_texto = dias_sem[now.weekday()]
        
        total_dias_mes = calendar.monthrange(now.year, now.month)[1]
        mes_pct = int((now.day / total_dias_mes) * 100)
        segundos_transcurridos = now.hour * 3600 + now.minute * 60 + now.second
        dia_pct = int((segundos_transcurridos / 86400) * 100)

        header = QHBoxLayout(); header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Progreso del Día y Mes"); title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        toggle_btn = QPushButton(icon=qta.icon("mdi.calendar-month" if not self.showing_month_grid else "mdi.chart-donut", color="white"))
        toggle_btn.setObjectName("ActionButton"); toggle_btn.setFixedSize(30, 30); toggle_btn.setToolTip("Alternar vista")
        toggle_btn.clicked.connect(self.toggle_month_grid_view)

        web_btn = self.create_action_button("month"); web_btn.setFixedSize(30, 30); web_btn.setToolTip("Abrir configuración")

        header.addWidget(title); header.addStretch(); header.addWidget(toggle_btn); header.addWidget(web_btn)
        l.addLayout(header)

        if self.showing_month_grid:
            # VISTA CALENDARIO MENSUAL COMPLETA CON EL DÍA ACTUAL RESALTADO (IDÉNTICO A LA FOTO)
            self.MONTH_W, self.MONTH_H = 460, 260
            
            cal_grid = QGridLayout()
            cal_grid.setSpacing(4)
            cal_grid.setContentsMargins(0, 6, 0, 0)
            
            dias_headers = ["DO", "LU", "MA", "MI", "JU", "VI", "SA"]
            for col, h_name in enumerate(dias_headers):
                hl = QLabel(h_name)
                hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                hl.setStyleSheet("color: #FFFFFF; font-size: 11px; font-weight: bold; padding-bottom: 4px;")
                cal_grid.addWidget(hl, 0, col)
            
            cal_obj = calendar.Calendar(firstweekday=6)
            month_days = cal_obj.monthdayscalendar(now.year, now.month)
            
            prev_month = now.month - 1 if now.month > 1 else 12
            prev_year = now.year if now.month > 1 else now.year - 1
            days_in_prev_month = calendar.monthrange(prev_year, prev_month)[1]
            
            next_day_counter = 1
            
            for row_idx, week in enumerate(month_days):
                for col_idx, day_num in enumerate(week):
                    day_container = QWidget()
                    day_container.setFixedSize(34, 30)
                    day_layout = QVBoxLayout(day_container)
                    day_layout.setContentsMargins(0, 0, 0, 0)
                    day_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    day_lbl = QLabel()
                    day_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    if day_num == 0:
                        if row_idx == 0:
                            zeros_count = week.count(0)
                            calc_day = days_in_prev_month - zeros_count + col_idx + 1
                            day_lbl.setText(str(calc_day))
                        else:
                            day_lbl.setText(str(next_day_counter))
                            next_day_counter += 1
                        day_lbl.setStyleSheet("color: rgba(255, 255, 255, 35); font-size: 12px; font-weight: 500;")
                    else:
                        day_lbl.setText(str(day_num))
                        if day_num == now.day:
                            day_lbl.setFixedSize(28, 28)
                            day_lbl.setStyleSheet("""
                                background-color: #38C7FE;
                                color: #000000;
                                border-radius: 14px;
                                font-size: 12px;
                                font-weight: bold;
                            """)
                        else:
                            day_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600;")
                    
                    day_layout.addWidget(day_lbl)
                    cal_grid.addWidget(day_container, row_idx + 1, col_idx)
            
            l.addLayout(cal_grid)
        else:
            self.MONTH_W, self.MONTH_H = 450, 210
            rings_layout = QHBoxLayout(); rings_layout.setSpacing(25); rings_layout.setContentsMargins(0, 0, 0, 0)
            rings_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.ring_mes = ProgressRingWidget("Mes", label_mes_texto, mes_pct, "#00A0FF")
            self.ring_dia = ProgressRingWidget("Día", label_dia_texto, dia_pct, "#00FF80")
            rings_layout.addWidget(self.ring_mes); rings_layout.addWidget(self.ring_dia)
            l.addLayout(rings_layout)

        return w

    def toggle_month_grid_view(self):
        self.showing_month_grid = not self.showing_month_grid
        self.month_panel.hide(); self.month_panel.setParent(None); self.month_panel.deleteLater()
        self.month_panel = self.create_month_panel()
        self.content_layout.insertWidget(3, self.month_panel)
        self.month_panel.show()
        self.execute_liquid_transition()

    def create_clipboard_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(20, 10, 20, 15); l.setSpacing(8)
        header = QHBoxLayout(); title = QLabel("Historial del Portapapeles"); title.setStyleSheet("font-weight: bold; font-size: 14px;")
        clear_btn = QPushButton("Limpiar")
        clear_btn.setStyleSheet("QPushButton { background-color: rgba(255,255,255,10); color: #CCC; border-radius: 6px; padding: 3px 8px; font-size: 10px; } QPushButton:hover { background-color: rgba(255,255,255,20); color: white; }")
        clear_btn.clicked.connect(self.clear_clipboard_history)
        header.addWidget(title); header.addStretch(); header.addWidget(clear_btn); l.addLayout(header)

        self.clipboard_list = QListWidget()
        self.clipboard_list.setStyleSheet(f"QListWidget {{ background: transparent; border: none; }} QListWidget::item {{ background: rgba(255,255,255,8); border-radius: 6px; padding: 6px 10px; margin-bottom: 4px; color: white; font-size: 11px; }} QListWidget::item:selected {{ background: {self.accent_color}; }}")
        self.clipboard_list.itemClicked.connect(self.copy_selected_clipboard)
        l.addWidget(self.clipboard_list); return w

    def check_clipboard(self):
        try:
            clipboard = QGuiApplication.clipboard(); text = clipboard.text()
            if text and text != self._last_clipboard_text:
                self._last_clipboard_text = text
                if text not in self.clipboard_history:
                    self.clipboard_history.insert(0, text)
                    if len(self.clipboard_history) > 10: self.clipboard_history.pop()
                    self.refresh_clipboard_ui()
        except: pass

    def refresh_clipboard_ui(self):
        if hasattr(self, 'clipboard_list'):
            self.clipboard_list.clear()
            for item_text in self.clipboard_history:
                display_text = item_text.replace("\n", " ")
                if len(display_text) > 45: display_text = display_text[:42] + "..."
                self.clipboard_list.addItem(QListWidgetItem(display_text))

    def copy_selected_clipboard(self, item):
        row = self.clipboard_list.row(item)
        if 0 <= row < len(self.clipboard_history):
            QGuiApplication.clipboard().setText(self.clipboard_history[row])
            self.show_notification("Portapapeles", "¡Copiado!", "Elemento copiado de nuevo al portapapeles")

    def clear_clipboard_history(self):
        self.clipboard_history.clear(); self.refresh_clipboard_ui()

    def create_basics_panel(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(20, 10, 20, 15)
        l.setSpacing(10)
        
        header = QHBoxLayout()
        title = QLabel("Atajos del Sistema")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        header.addWidget(title)
        header.addStretch()
        l.addLayout(header)

        # Fila horizontal única
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for item in SYSTEM_SHORTCUTS:
            btn = QPushButton(icon=qta.icon(item["icon"], color="white"))
            btn.setFixedSize(42, 42)
            btn.setToolTip(item["name"])
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 14);
                    border: 1px solid rgba(255, 255, 255, 20);
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    background-color: {item.get('color', '#00A0FF')};
                    border: 1px solid white;
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 40);
                }}
            """)
            if item.get("action") == "toggle_theme":
                btn.clicked.connect(self.toggle_system_theme)
            else:
                cmd = item["cmd"]
                btn.clicked.connect(lambda _, c=cmd: subprocess.Popen(c, shell=True))
            row.addWidget(btn)

        l.addLayout(row)
        return w

    def create_pomodoro_panel(self):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(25, 12, 25, 15); l.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel("Pomodoro"); title.setStyleSheet("font-weight: bold; font-size: 15px;")
        
        custom_time_btn = QPushButton(icon=qta.icon("mdi.clock-outline", color="white"))
        custom_time_btn.setObjectName("ActionButton"); custom_time_btn.setFixedSize(28, 28)
        custom_time_btn.setToolTip("Configurar tiempo personalizado")
        custom_time_btn.clicked.connect(self.set_custom_pomodoro_time)

        self.pomo_mode_lbl = QLabel("CONCENTRACIÓN (25m)"); self.pomo_mode_lbl.setStyleSheet("color: #FF6B6B; font-size: 11px; font-weight: 700;")
        header.addWidget(title); header.addStretch(); header.addWidget(custom_time_btn); header.addSpacing(4); header.addWidget(self.pomo_mode_lbl)
        l.addLayout(header)
        
        self.pomo_time_lbl = QLabel("25:00"); self.pomo_time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomo_time_lbl.setStyleSheet("font-size: 36px; font-weight: bold; color: white; letter-spacing: 2px;")
        l.addWidget(self.pomo_time_lbl)
        
        ctrl_layout = QHBoxLayout(); ctrl_layout.setSpacing(12); ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_style = "QPushButton { background-color: rgba(255,255,255,15); color: white; border-radius: 14px; padding: 6px 14px; font-weight: 600; font-size: 12px; border: 1px solid rgba(255,255,255,20); } QPushButton:hover { background-color: rgba(255,255,255,30); }"
        
        self.pomo_btn_toggle = QPushButton("Iniciar"); self.pomo_btn_toggle.setStyleSheet(btn_style); self.pomo_btn_toggle.clicked.connect(self.toggle_pomodoro)
        self.pomo_btn_reset = QPushButton("Reiniciar"); self.pomo_btn_reset.setStyleSheet(btn_style); self.pomo_btn_reset.clicked.connect(self.reset_pomodoro)
        self.pomo_btn_mode = QPushButton("Descanso (5m)"); self.pomo_btn_mode.setStyleSheet(btn_style); self.pomo_btn_mode.clicked.connect(self.switch_pomodoro_mode)
        
        ctrl_layout.addWidget(self.pomo_btn_toggle); ctrl_layout.addWidget(self.pomo_btn_reset); ctrl_layout.addWidget(self.pomo_btn_mode)
        l.addLayout(ctrl_layout); return w

    def set_custom_pomodoro_time(self):
        mins, ok = QInputDialog.getInt(self, "Personalizar Pomodoro", "Ingresa los minutos de concentración:", value=25, min=1, max=180)
        if ok:
            self.pomo_running = False; self.pomo_timer.stop()
            self.pomo_btn_toggle.setText("Iniciar"); self.pomo_mode = "Concentración"
            self.pomo_mode_lbl.setText(f"CONCENTRACIÓN ({mins}m)")
            self.pomo_time_left = mins * 60
            self.update_pomo_display(); self.update_content()

    def toggle_pomodoro(self):
        self.pomo_running = not self.pomo_running
        if self.pomo_running: self.pomo_btn_toggle.setText("Pausar"); self.pomo_timer.start(1000)
        else: self.pomo_btn_toggle.setText("Reanudar"); self.pomo_timer.stop()
        self.update_content()

    def reset_pomodoro(self):
        self.pomo_running = False; self.pomo_timer.stop(); self.pomo_btn_toggle.setText("Iniciar")
        current_mins = self.pomo_time_left // 60 if hasattr(self, 'pomo_time_left') else 25
        self.pomo_time_left = (current_mins * 60) if self.pomo_mode == "Concentración" else (5 * 60)
        self.update_pomo_display(); self.update_content()

    def switch_pomodoro_mode(self):
        if self.pomo_mode == "Concentración":
            self.pomo_mode = "Descanso"; self.pomo_mode_lbl.setText("DESCANSO (5m)")
            self.pomo_mode_lbl.setStyleSheet("color: #00FF80; font-size: 11px; font-weight: 700;")
            self.pomo_btn_mode.setText("Concentración")
        else:
            self.pomo_mode = "Concentración"; self.pomo_mode_lbl.setText("CONCENTRACIÓN (25m)")
            self.pomo_mode_lbl.setStyleSheet("color: #FF6B6B; font-size: 11px; font-weight: 700;")
            self.pomo_btn_mode.setText("Descanso (5m)")
        self.reset_pomodoro()

    def tick_pomodoro(self):
        if self.pomo_time_left > 0:
            self.pomo_time_left -= 1; self.update_pomo_display(); self.update_content()
        else:
            self.pomo_running = False; self.pomo_timer.stop(); self.pomo_btn_toggle.setText("Iniciar")
            self.show_notification("Pomodoro", f"¡{self.pomo_mode} terminado!", "Ciclo completado con éxito")
            self.switch_pomodoro_mode()

    def update_pomo_display(self):
        m, s = divmod(self.pomo_time_left, 60)
        self.pomo_time_lbl.setText(f"{m:02d}:{s:02d}")

    def create_sliders_panel(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(25, 12, 25, 15)
        l.setSpacing(10)
        
        header = QHBoxLayout()
        title = QLabel("Audio del Sistema")
        title.setStyleSheet("font-weight: bold; font-size: 15px; color: white;")
        header.addWidget(title)
        header.addStretch()
        l.addLayout(header)

        slider_style = """
            QSlider::groove:horizontal { background: rgba(255,255,255,25); height: 6px; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #00D2FF; border-radius: 3px; }
            QSlider::handle:horizontal { background: white; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }
        """

        # --- SLIDER GENERAL ---
        vol_row = QHBoxLayout()
        vol_row.setSpacing(10)
        vol_ico = QLabel()
        vol_ico.setPixmap(qta.icon("mdi.volume-high", color="white").pixmap(18, 18))
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setStyleSheet(slider_style)
        self.vol_val_lbl = QLabel("0%")
        self.vol_val_lbl.setFixedWidth(35)
        self.vol_val_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: white;")
        
        self.vol_slider.valueChanged.connect(lambda v: self.vol_val_lbl.setText(f"{v}%"))
        self.vol_slider.sliderReleased.connect(self.apply_volume_change)
        
        vol_row.addWidget(vol_ico)
        vol_row.addWidget(self.vol_slider)
        vol_row.addWidget(self.vol_val_lbl)
        l.addLayout(vol_row)

        # --- BOTONES EXTRA (Estilo Toggle) ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_style_normal = """
            QPushButton { 
                background-color: rgba(255, 255, 255, 12); 
                border: 1px solid rgba(255, 255, 255, 20); 
                border-radius: 10px; 
                color: white; 
            } 
            QPushButton:hover { background-color: rgba(255, 255, 255, 25); }
        """
        self.btn_style_active = """
            QPushButton { 
                background-color: #00D2FF; 
                border: 1px solid #00D2FF; 
                border-radius: 10px; 
                color: black; 
            } 
            QPushButton:hover { background-color: #33DDFF; }
        """

        self.btn_mute_mic = QPushButton(icon=qta.icon("mdi.microphone", color="white"))
        self.btn_mute_mic.setFixedSize(80, 32)
        self.btn_mute_mic.setToolTip("Mutear / Desmutear Micrófono")
        self.btn_mute_mic.setStyleSheet(self.btn_style_normal)
        self.btn_mute_mic.clicked.connect(self.toggle_mute_mic)

        self.btn_deafen = QPushButton(icon=qta.icon("mdi.headphones", color="white"))
        self.btn_deafen.setFixedSize(80, 32)
        self.btn_deafen.setToolTip("Ensordecer / Escuchar")
        self.btn_deafen.setStyleSheet(self.btn_style_normal)
        self.btn_deafen.clicked.connect(self.toggle_deafen)

        btn_row.addWidget(self.btn_mute_mic)
        btn_row.addWidget(self.btn_deafen)
        l.addLayout(btn_row)

        self._last_vol = self.vol_slider.value()
        return w

    def toggle_mute_mic(self):
        self.mic_muted = not getattr(self, 'mic_muted', False)
        
        if self.mic_muted:
            self.btn_mute_mic.setStyleSheet(self.btn_style_active)
            self.btn_mute_mic.setIcon(qta.icon("mdi.microphone-off", color="black"))
        else:
            self.btn_mute_mic.setStyleSheet(self.btn_style_normal)
            self.btn_mute_mic.setIcon(qta.icon("mdi.microphone", color="white"))
            
    def toggle_deafen(self):
        self.deafened = not getattr(self, 'deafened', False)
        
        if self.deafened:
            self.btn_deafen.setStyleSheet(self.btn_style_active)
            self.btn_deafen.setIcon(qta.icon("mdi.headphones-off", color="black"))
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)
        else:
            self.btn_deafen.setStyleSheet(self.btn_style_normal)
            self.btn_deafen.setIcon(qta.icon("mdi.headphones", color="white"))
            ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)

    def toggle_mute_system(self):
        ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xAD, 0, 2, 0)

    def toggle_system_theme(self):
        """Alterna entre modo oscuro y claro del sistema (Windows 10/11)."""
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)

            try:
                current, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            except FileNotFoundError:
                current = 0  # por defecto asumimos oscuro

            new_value = 0 if current == 1 else 1
            winreg.SetValueEx(key, "AppsUseLightTheme",   0, winreg.REG_DWORD, new_value)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, new_value)
            winreg.CloseKey(key)

            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageW(
                HWND_BROADCAST, WM_SETTINGCHANGE, 0, ctypes.c_wchar_p("ImmersiveColorSet")
            )

            mode_name = "Claro ☀️" if new_value == 1 else "Oscuro 🌙"
            self.show_notification("Tema del Sistema", f"Modo {mode_name}", "Cambio aplicado correctamente")
        except Exception as e:
            self.show_notification("Tema del Sistema", "Error", f"No se pudo cambiar el tema: {e}")

    def apply_volume_change(self):
        target = self.vol_slider.value()
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            
            # Nueva forma correcta de obtener el dispositivo en pycaw
            device = AudioUtilities.GetSpeakers()
            interface = device.EndpointVolume
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(target / 100.0, None)
        except Exception as e:
            print(f"Error al ajustar volumen maestro: {e}")
        self._last_vol = target

    def get_system_volume(self):
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            
            device = AudioUtilities.GetSpeakers()
            interface = device.EndpointVolume
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            return int(volume.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            return 50

    def update_content(self):
        if self.current_state == "Idle":
            feature = self.features[self.current_feature_index]
            if self.pomo_running:
                m, s = divmod(self.pomo_time_left, 60)
                color = "#FF6B6B" if self.pomo_mode == "Concentración" else "#00FF80"
                self.status_text.setText(f"{self.pomo_mode}: {m:02d}:{s:02d}")
                self.status_icon.setPixmap(qta.icon('mdi.timer-outline', color=color).pixmap(18, 18))
            elif feature == "media" and self.media_state in ("Playing", "Paused"):
                if self.showing_lyrics and self.media_lyric_text:
                    self.status_text.setText(self.media_lyric_text)
                else:
                    dt = self.media_title; self.status_text.setText(dt[:22] + "..." if len(dt) > 25 else dt)
                self.status_icon.setPixmap(qta.icon('mdi.music', color='white').pixmap(18, 18))
            else:
                try:
                    # Forzar idioma español para el día de la semana
                    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
                except:
                    try:
                        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
                    except:
                        pass
                
                now = datetime.datetime.now()
                # Formato 12h con AM/PM (puedes cambiarlo a 24h si prefieres)
                ts = now.strftime("%I:%M %p").lstrip("0")
                dia_semana = now.strftime("%A").capitalize()
                
                self.status_text.setText(f"{dia_semana}, {ts}")
                self.status_icon.setPixmap(qta.icon('mdi.circle', color=self.accent_color).pixmap(18, 18))
        self.update()

    def update_media(self, state, title, artist, accent_hex):
        self.media_state, self.media_title, self.media_artist = state, title, artist; self.album_accent_color = QColor(accent_hex)
        self.btn_play.setIcon(qta.icon('mdi.pause' if state == "Playing" else 'mdi.play', color='white'))
        self.update_content()

    def update_lyrics(self, text):
        self.media_lyric_text = text; self.showing_lyrics = bool(text); self.update_content()

    def update_feature_view(self):
        if self.current_state == "Idle":
            for p in [self.weather_panel, self.calendar_panel, self.month_panel, self.pomo_panel, self.sliders_panel, self.clipboard_panel, self.search_panel, self.apps_panel, self.basics_panel]: p.hide()
            self.media_controls.hide()
            self.island_weather_widget.show()
            self.header_widget.show(); self.update_content(); return
        if self.current_state == "Notify":
            for p in [self.weather_panel, self.calendar_panel, self.month_panel, self.pomo_panel, self.sliders_panel, self.clipboard_panel, self.search_panel, self.apps_panel, self.basics_panel]: p.hide()
            self.media_controls.hide(); self.header_widget.show()
            self.island_weather_widget.hide()
            self.status_icon.setPixmap(qta.icon('mdi.lightning-bolt' if "Lock" in self.event_title else 'mdi.email', color='white').pixmap(18, 18))
            dt = f"{self.event_title} - {self.event_text}"; self.status_text.setText(dt[:45] + "..." if len(dt) > 48 else dt)
            return
            
        feature = self.features[self.current_feature_index]
        self.header_widget.show() if feature == "media" else self.header_widget.hide()
        self.island_weather_widget.hide()
        
        self.media_controls.setVisible(feature == "media")
        self.weather_panel.setVisible(feature == "weather")
        self.calendar_panel.setVisible(feature == "calendar")
        self.month_panel.setVisible(feature == "month")
        self.pomo_panel.setVisible(feature == "pomodoro")
        self.sliders_panel.setVisible(feature == "sliders")
        
        if feature == "sliders" and self.current_state == "Hover":
            # Sincronizar el slider maestro con el volumen real de Windows al abrir
            real_vol = self.get_system_volume()
            self.vol_slider.blockSignals(True)
            self.vol_slider.setValue(real_vol)
            self.vol_val_lbl.setText(f"{real_vol}%")
            self._last_vol = real_vol
            self.vol_slider.blockSignals(False)
            
        self.clipboard_panel.setVisible(feature == "clipboard")
        self.search_panel.setVisible(feature == "search")
        self.apps_panel.setVisible(feature == "apps")
        self.basics_panel.setVisible(feature == "basics")

        if feature == "clipboard": self.status_text.setText("Historial del Portapapeles"); self.status_icon.setPixmap(qta.icon('mdi.clipboard-text', color='white').pixmap(18, 18))
        elif feature == "search": self.status_text.setText("Búsqueda Rápida"); self.status_icon.setPixmap(qta.icon('mdi.magnify', color='white').pixmap(18, 18))
        elif feature == "apps": self.status_text.setText("Aplicaciones Frecuentes"); self.status_icon.setPixmap(qta.icon('mdi.view-grid', color='white').pixmap(18, 18))
        elif feature == "basics": self.status_text.setText("Atajos del Sistema"); self.status_icon.setPixmap(qta.icon('mdi.cog', color='white').pixmap(18, 18))
        elif feature == "media":
            if self.media_state in ("Playing", "Paused"):
                if self.showing_lyrics and self.media_lyric_text:
                    self.status_text.setText(self.media_lyric_text)
                else:
                    dt = f"{self.media_title} - {self.media_artist}"; self.status_text.setText(dt[:37] + "..." if len(dt) > 40 else dt)
            else: self.status_text.setText("Reproductor Musical")
            self.status_icon.setPixmap(qta.icon('mdi.music', color='white').pixmap(18, 18))

    def wheelEvent(self, event):
        if self.current_state == "Hover" and not self.is_editing_tasks:
            delta = event.angleDelta().y()
            self.current_feature_index = (self.current_feature_index + (1 if delta < 0 else -1)) % len(self.features)
            self.execute_liquid_transition()
        super().wheelEvent(event)

    def keyPressEvent(self, event): super().keyPressEvent(event)

    def get_centered_x(self, width):
        sr = self.screen().availableGeometry(); return sr.x() + (sr.width() // 2) - (width // 2)

    def execute_liquid_transition(self):
        if self.is_charging: w, h = 850, 40
        elif self.current_state == "Idle": w, h = self.IDLE_W, self.IDLE_H
        elif self.current_state == "Notify": w, h = self.NOTIFY_W, self.NOTIFY_H
        else:
            feature = self.features[self.current_feature_index]
            if feature == "media": w, h = self.MUSIC_W, self.MUSIC_H
            elif feature == "weather": w, h = self.WEATHER_W, self.WEATHER_H
            elif feature == "calendar": w, h = (self.EDIT_W, self.EDIT_H) if self.is_editing_tasks else (self.CALENDAR_W, self.CALENDAR_H)
            elif feature == "month": 
                w, h = (460, 260) if self.showing_month_grid else (450, 210)
            elif feature == "pomodoro": w, h = self.POMO_W, self.POMO_H
            elif feature == "sliders": w, h = self.SLIDERS_W, self.SLIDERS_H
            elif feature == "clipboard": w, h = self.CLIPBOARD_W, self.CLIPBOARD_H
            elif feature == "search": w, h = self.SEARCH_W, self.SEARCH_H
            elif feature == "apps": w, h = self.APPS_W, self.APPS_H
            elif feature == "basics": w, h = self.BASICS_W, self.BASICS_H 
            else: w, h = self.EXP_W, self.EXP_H
            
        if not self.is_charging:
             self.shine_anim.stop(); self.shine_anim.setStartValue(0.0); self.shine_anim.setEndValue(1.0); self.shine_anim.start()
        
        is_hover = (self.current_state != "Idle" and self.current_state != "Notify")
        feat = self.features[self.current_feature_index] if is_hover else None
        
        for f in ["weather", "calendar", "month", "pomodoro", "sliders", "clipboard", "search", "apps", "basics"]:
            anim = getattr(self, f"{f}_bg_anim")
            anim.stop(); anim.setStartValue(getattr(self, f"_{f}_bg_opacity"))
            anim.setEndValue(1.0 if feat == f else 0.0); anim.start()

        self.anim_group.stop()
        self.content_pos_anim.setStartValue(QPoint(0, 0)); self.content_pos_anim.setEndValue(QPoint(0, 0))
        self.opacity_anim.setStartValue(1.0); self.opacity_anim.setKeyValueAt(0.3, 0.0); self.opacity_anim.setEndValue(1.0)
        self.island_w_anim.setStartValue(self._island_w); self.island_w_anim.setEndValue(w)
        self.island_h_anim.setStartValue(self._island_h); self.island_h_anim.setEndValue(h)
        QTimer.singleShot(200, self.update_feature_view)
        self.anim_group.start()

    def change_state(self, new):
        if self.current_state == new: return
        self.current_state = new; self.execute_liquid_transition()

    def set_island_style(self, style):
        self.island_style = style
        self.save_settings()
        self.recenter_window()
        self.execute_liquid_transition()
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())
        self.update()

    def set_animation_style(self, style):
        self.animation_style = style
        self.save_settings()
        self.update()

    def get_island_rect(self):
        W = self._island_w; H = self._island_h; centerX = self.width() / 2
        return QRectF(centerX - W/2, 0, W, H) if self.island_style == "Notch Nook" else QRectF(centerX - W/2, 10, W, H)

    def recenter_window(self):
        if self.compatibility_mode:
            self.setMinimumSize(0, 0); self.setMaximumSize(16777215, 16777215)
            self.setGeometry(self.screen().availableGeometry())
        else:
            self.setFixedSize(1200, 700)
            self.move(self.get_centered_x(self.width()), 0 if self.island_style == "Notch Nook" else 10)

    def toggle_compatibility_mode(self):
        self.compatibility_mode = not self.compatibility_mode
        self.save_settings()
        self.recenter_window()
        self.update_island_geometry(self.get_island_rect(), self.get_current_radius())
        self.update()

    def check_mouse_position(self):
        if self.current_state == "Notify" or self.is_dialog_open: return
        cursor_pos = QCursor.pos(); rect = self.get_island_rect()
        global_rect = QRect(self.mapToGlobal(QPoint(int(rect.x()), int(rect.y()))), self.mapToGlobal(QPoint(int(rect.right()), int(rect.bottom()))))
        hit_rect = global_rect.adjusted(-15, -10, 80, 50)
        hwnd = int(self.winId()); ex = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        
        if hit_rect.contains(cursor_pos):
            if ex & 0x20: ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex & ~0x20)
            if self.current_state != "Hover": self.change_state("Hover")
            self.revert_timer.stop()
        else:
            if not (ex & 0x20): ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex | 0x20)
            if self.current_state == "Hover" and not self.revert_timer.isActive():
                self.revert_timer.start(1200)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #1a1a1a; color: #fff; border: 1px solid #333; padding: 4px; border-radius: 6px; } QMenu::item:selected { background-color: " + self.accent_color + "; }")
        
        lock_action = menu.addAction("Fija / Estática (Bloqueada)")
        lock_action.setCheckable(True)
        lock_action.setChecked(self.is_locked)
        lock_action.triggered.connect(self.toggle_lock_position)

        menu.addSeparator()
        
        sm = menu.addMenu("Estilo de Isla")
        for s in ["Por Defecto", "Liquid Glass", "Notch Nook"]:
            a = sm.addAction(s)
            a.setCheckable(True)
            a.setChecked(self.island_style == s)
            a.triggered.connect(lambda _, st=s: self.set_island_style(st))

        am = menu.addMenu("Estilo de Animación")
        for s in ["Barrido Neón", "Burbujas Fluidas", "Borde LED"]:
            a = am.addAction(s)
            a.setCheckable(True)
            a.setChecked(self.animation_style == s)
            a.triggered.connect(lambda _, st=s: self.set_animation_style(st))

        menu.addSeparator()

        comp_action = menu.addAction("Modo Compatibilidad (Fix)")
        comp_action.setCheckable(True)
        comp_action.setChecked(self.compatibility_mode)
        comp_action.triggered.connect(self.toggle_compatibility_mode)
        
        loc_action = menu.addAction("Cambiar Ubicación (Clima)")
        loc_action.triggered.connect(self.change_location_dialog)
        
        menu.addSeparator()
        qa = menu.addAction("Salir")
        qa.triggered.connect(self.close)
        menu.exec(self.mapToGlobal(event.pos()))

    def closeEvent(self, event):
        self.media_monitor.stop(); self.key_monitor.stop(); self.notif_monitor.stop(); self.weather_monitor.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv); island = DynamicIsland(); island.show()
    sys.exit(app.exec())