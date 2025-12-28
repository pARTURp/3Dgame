from direct.gui.DirectGui import *
from panda3d.core import TextNode, WindowProperties
import sys

class UIManager:
    def __init__(self, game):
        self.game = game
        self.main_menu_frame = None
        self.game_ui_frame = None
        self.book_frame = None
        self.game_over_frame = None  # Добавлено для хранения окна смерти
        self.player_ref = None
        self.is_menu_open = False
        self.notification_label = None
        
        self.current_tab = "spells" 
        self.current_spell_idx = 0

    def hide_all_menus(self):
        if self.main_menu_frame: self.main_menu_frame.hide()
        if self.book_frame: self.book_frame.hide()
        if self.game_over_frame: self.game_over_frame.hide() # Скрываем окно смерти
        if self.game_ui_frame: self.game_ui_frame.show()
        self.is_menu_open = False

    def show_main_menu(self, start_callback):
        self.is_menu_open = True
        if self.game_ui_frame: self.game_ui_frame.hide()
        if self.main_menu_frame: self.main_menu_frame.destroy()
        if self.game_over_frame: self.game_over_frame.destroy() # Удаляем окно смерти при переходе в меню
        
        self.main_menu_frame = DirectFrame(frameColor=(0, 0, 0, 1), frameSize=(-1, 1, -1, 1))
        DirectLabel(parent=self.main_menu_frame, text="THE VOID", scale=0.15, pos=(0, 0, 0.6), text_fg=(1, 1, 1, 1))
        DirectLabel(parent=self.main_menu_frame, text="Start with nothing. Learn to move.", scale=0.06, pos=(0, 0, 0.4), text_fg=(0.7, 0.7, 0.7, 1))
        DirectButton(parent=self.main_menu_frame, text="Enter", scale=0.1, pos=(0, 0, 0), command=start_callback)
        DirectButton(parent=self.main_menu_frame, text="Quit", scale=0.1, pos=(0, 0, -0.2), command=sys.exit)

    def setup_game_ui(self, player):
        self.player_ref = player
        if self.game_ui_frame: self.game_ui_frame.destroy()
        self.game_ui_frame = DirectFrame(frameColor=(0,0,0,0), frameSize=(-1, 1, -1, 1))
        
        self.health_label = DirectLabel(parent=self.game_ui_frame, text="HP: 100", scale=0.07, pos=(-1.1, 0, 0.9), text_align=TextNode.ALeft, text_fg=(1,0,0,1))
        self.crosshair = DirectLabel(parent=self.game_ui_frame, text=".", scale=0.1, pos=(0, 0, -0.02), text_fg=(1, 1, 0, 1))
        
        self.prompt = DirectLabel(parent=self.game_ui_frame, text="[E] Read", scale=0.07, pos=(0, 0, -0.2), text_fg=(1, 1, 1, 1))
        self.prompt.hide()
        
        self.notification_label = DirectLabel(parent=self.game_ui_frame, text="", scale=0.06, pos=(0, 0, 0.7), text_fg=(1, 1, 0, 1), frameColor=(0,0,0,0))
        self.notification_label.hide()

    def show_notification(self, text):
        if self.notification_label:
            self.notification_label['text'] = text
            self.notification_label.show()
            self.game.taskMgr.doMethodLater(3.0, lambda t: self.notification_label.hide(), 'hidenotify')

    def show_interact_prompt(self, show):
        if not self.prompt: return
        if show: self.prompt.show()
        else: self.prompt.hide()

    def update(self, dt):
        if not self.player_ref or not self.health_label: return
        self.health_label['text'] = f"HP: {int(self.player_ref.health)}"

    def flash_damage(self):
        f = DirectFrame(frameColor=(1, 0, 0, 0.3), frameSize=(-2, 2, -2, 2))
        f.setTransparency(True)
        self.game.taskMgr.doMethodLater(0.2, lambda t: f.destroy(), 'flash')

    # --- КНИГА (ESC) ---
    def toggle_book_ui(self):
        if self.book_frame and not self.book_frame.isHidden():
            self.book_frame.hide()
            self.is_menu_open = False
            props = WindowProperties()
            props.setCursorHidden(True)
            props.setMouseMode(WindowProperties.M_relative)
            self.game.win.requestProperties(props)
        else:
            self.build_book_ui()
            self.book_frame.show()
            self.is_menu_open = True
            props = WindowProperties()
            props.setCursorHidden(False)
            props.setMouseMode(WindowProperties.M_absolute)
            self.game.win.requestProperties(props)

    def build_book_ui(self):
        if self.book_frame: self.book_frame.destroy()
        
        self.book_frame = DirectFrame(frameColor=(0.4, 0.25, 0.1, 1), frameSize=(-1.2, 1.2, -0.8, 0.8))
        self.page_left = DirectFrame(parent=self.book_frame, frameColor=(0.9, 0.85, 0.7, 1), frameSize=(-1.1, -0.1, -0.7, 0.7))
        self.page_right = DirectFrame(parent=self.book_frame, frameColor=(0.9, 0.85, 0.7, 1), frameSize=(0.1, 1.1, -0.7, 0.7))
        
        DirectButton(parent=self.page_left, text="Spells", scale=0.06, pos=(-0.8, 0, 0.6), command=self.set_tab, extraArgs=["spells"])
        DirectButton(parent=self.page_left, text="System", scale=0.06, pos=(-0.5, 0, 0.6), command=self.set_tab, extraArgs=["system"])
        
        self.content_node = DirectFrame(parent=self.book_frame, frameColor=(0,0,0,0))
        self.refresh_book_content()

    def set_tab(self, tab):
        self.current_tab = tab
        self.refresh_book_content()

    def refresh_book_content(self):
        self.content_node.destroy()
        self.content_node = DirectFrame(parent=self.book_frame, frameColor=(0,0,0,0))
        
        if self.current_tab == "spells":
            self.draw_spells_tab()
        elif self.current_tab == "system":
            self.draw_system_tab()

    def draw_spells_tab(self):
        unlocked = [k for k, v in self.player_ref.abilities.abilities.items() if v["unlocked"]]
        
        if not unlocked:
            DirectLabel(parent=self.content_node, text="Empty...", scale=0.1, pos=(-0.6, 0, 0), text_fg=(0.5,0.5,0.5,1))
            return

        if self.current_spell_idx >= len(unlocked): self.current_spell_idx = 0
            
        key = unlocked[self.current_spell_idx]
        data = self.player_ref.abilities.abilities[key]
        
        DirectLabel(parent=self.content_node, text=data["name"], scale=0.12, pos=(-0.6, 0, 0.3), text_fg=(0,0,0,1))
        DirectLabel(parent=self.content_node, text=data["description"], scale=0.06, pos=(-0.6, 0, 0.1), text_fg=(0.2,0.2,0.2,1), text_wordwrap=12)
        
        if len(unlocked) > 1:
            DirectButton(parent=self.content_node, text="Next >", scale=0.08, pos=(0.6, 0, -0.5), command=self.next_spell)
            
        DirectLabel(parent=self.content_node, text=f"{self.current_spell_idx + 1}/{len(unlocked)}", scale=0.05, pos=(0.6, 0, -0.6), text_fg=(0,0,0,1))

    def next_spell(self):
        unlocked = [k for k, v in self.player_ref.abilities.abilities.items() if v["unlocked"]]
        self.current_spell_idx = (self.current_spell_idx + 1) % len(unlocked)
        self.refresh_book_content()

    def draw_system_tab(self):
        # Настройка чувствительности
        DirectLabel(parent=self.content_node, text="Mouse Sens", scale=0.05, pos=(-0.6, 0, 0.1), text_fg=(0,0,0,1))
        self.sens_slider = DirectSlider(parent=self.content_node, range=(0.05, 1.0), value=self.player_ref.mouse_sensitivity, pageSize=0.1, pos=(-0.6, 0, 0), scale=0.3, command=self.update_sens)
        
        # Настройка FOV
        DirectLabel(parent=self.content_node, text="FOV", scale=0.05, pos=(-0.6, 0, -0.1), text_fg=(0,0,0,1))
        current_fov = self.game.camLens.getFov()[0]
        self.fov_slider = DirectSlider(parent=self.content_node, range=(60, 110), value=current_fov, pageSize=5, pos=(-0.6, 0, -0.2), scale=0.3, command=self.update_fov)
        
        DirectButton(parent=self.content_node, text="Exit to Menu", scale=0.08, pos=(-0.6, 0, -0.4), command=self.game.exit_to_menu)

    def update_sens(self):
        if self.player_ref:
            self.player_ref.mouse_sensitivity = self.sens_slider['value']

    def update_fov(self):
        if hasattr(self, 'fov_slider'):
            new_fov = self.fov_slider['value']
            self.game.camLens.setFov(new_fov)

    def show_game_over(self):
        self.is_menu_open = True
        if self.game_ui_frame: self.game_ui_frame.hide()
        if self.game_over_frame: self.game_over_frame.destroy()
        
        # Сохраняем окно в self, чтобы потом можно было удалить
        self.game_over_frame = DirectFrame(frameColor=(0, 0, 0, 0.8), frameSize=(-1, 1, -1, 1))
        DirectLabel(parent=self.game_over_frame, text="YOU DIED", scale=0.15, pos=(0, 0, 0.1), text_fg=(1, 0, 0, 1))
        DirectButton(parent=self.game_over_frame, text="Menu", scale=0.1, pos=(0, 0, -0.2), command=self.game.exit_to_menu)
