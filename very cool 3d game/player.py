from panda3d.core import Vec3, CollisionRay, CollisionNode, CollisionHandlerQueue, BitMask32
from panda3d.core import WindowProperties, CollisionSphere
from direct.showbase.InputStateGlobal import inputState
from abilities import AbilitySystem
import random

class Player:
    def __init__(self, game):
        self.game = game
        self.speed = 15
        self.health = 100
        self.vertical_velocity = 0
        self.is_grounded = False
        
        self.abilities = AbilitySystem()
        
        # Загрузка модели (Box)
        self.model = game.loader.loadModel("models/box")
        self.model.setScale(0.5, 0.5, 1)
        
        # Стартовая позиция над землей
        z = game.get_terrain_height(0, 0) + 5
        self.model.setPos(0, 0, z)
        self.model.reparentTo(game.render)

        # 1. Физика тела (Стены/Враги) - Bit 0
        self.collider = self.model.attachNewNode(CollisionNode('player'))
        self.collider.node().addSolid(CollisionSphere(0, 0, 0, 1))
        # Collide with Bit 0 (Walls/Enemies), ignore Bit 2 (Terrain) to prevent sliding
        self.collider.node().setFromCollideMask(BitMask32.bit(0))
        self.collider.node().setIntoCollideMask(BitMask32.allOff())
        game.cTrav.addCollider(self.collider, game.pusher)
        game.pusher.addCollider(self.collider, self.model)
        
        # 2. Физика гравитации (Земля) - Bit 2
        self.gravity_ray = CollisionRay(0, 0, 0.5, 0, 0, -1)
        self.gravity_node = self.model.attachNewNode(CollisionNode('playerRay'))
        self.gravity_node.node().addSolid(self.gravity_ray)
        # Track Bit 2 (Terrain)
        self.gravity_node.node().setFromCollideMask(BitMask32.bit(2)) 
        self.gravity_node.node().setIntoCollideMask(BitMask32.allOff())
        
        self.gravity_handler = CollisionHandlerQueue()
        game.cTrav.addCollider(self.gravity_node, self.gravity_handler)

        # Камера
        game.camera.reparentTo(self.model)
        game.camera.setPos(0, 0, 0.6)
        self.camera_pitch = 0.0
        self.camera_heading = 0.0
        self.mouse_sensitivity = 0.2

        # 3. Луч для взаимодействия (Книги) - Bit 1
        self.picker_ray = CollisionRay(0, 0, 0, 0, 1, 0) 
        self.picker_node = CollisionNode('mouseRay')
        self.picker_node.addSolid(self.picker_ray)
        self.picker_node.setFromCollideMask(BitMask32.bit(1))
        self.picker_node.setIntoCollideMask(BitMask32.allOff())
        self.picker_np = game.camera.attachNewNode(self.picker_node)
        self.picker_handler = CollisionHandlerQueue()
        game.cTrav.addCollider(self.picker_np, self.picker_handler)

        self.setup_controls()
        
        # ХАРДКОР: Через 5 секунд пробуждается одно действие
        game.taskMgr.doMethodLater(5.0, self.initial_awakening, "InitialUnlock")
        game.taskMgr.add(self.update, "PlayerUpdate")
        self.hovered_book = None

    def initial_awakening(self, task):
        movements = ["move_forward", "move_backward", "move_left", "move_right"]
        chosen = random.choice(movements)
        self.abilities.abilities[chosen]["unlocked"] = True
        self.game.ui.show_notification(f"SUDDENLY: You can {self.abilities.abilities[chosen]['name']}!")
        return task.done

    def setup_controls(self):
        inputState.watchWithModifiers('forward', 'w')
        inputState.watchWithModifiers('backward', 's')
        inputState.watchWithModifiers('left', 'a')
        inputState.watchWithModifiers('right', 'd')
        inputState.watchWithModifiers('jump', 'space')
        
        self.game.accept('e', self.interact)
        # --- НОВОЕ: Стрельба ---
        self.game.accept('mouse1', self.shoot)
        
        self.game.accept('shift', self.use_ability_blink)
        self.game.accept('q', self.use_ability_shield)
        self.game.accept('escape', self.game.ui.toggle_book_ui)

    # --- НОВОЕ: Функция стрельбы ---
    def shoot(self):
        if self.game.ui.is_menu_open: return
        
        # Проверяем, открыта ли способность (или разрешаем базово, если нужно)
        # Но по логике игры всё должно быть закрыто. Добавим проверку.
        if self.abilities.is_unlocked("shoot"):
            cam_quat = self.game.camera.getQuat(self.game.render)
            fwd = cam_quat.getForward()
            # Позиция выстрела чуть перед камерой
            start_pos = self.game.camera.getPos(self.game.render) + fwd * 1.0
            self.game.spawn_projectile(start_pos, fwd)
        # Можно добавить else: звук "неудачи", но пока оставим тихо.

    def unlock_random_ability(self):
        locked = [k for k, v in self.abilities.abilities.items() if not v["unlocked"]]
        if not locked: return "Nothing (All Learned)"
        
        key = random.choice(locked)
        self.abilities.abilities[key]["unlocked"] = True
        return self.abilities.abilities[key]["name"]

    def cleanup(self):
        self.game.ignoreAll()
        if self.model: self.model.removeNode()

    def update(self, task):
        dt = globalClock.getDt()
        
        # Вращение камеры
        if self.game.mouseWatcherNode.hasMouse() and not self.game.ui.is_menu_open:
            md = self.game.win.getPointer(0)
            x = md.getX()
            y = md.getY()
            cx, cy = self.game.win.getXSize() // 2, self.game.win.getYSize() // 2
            if self.game.win.movePointer(0, cx, cy):
                self.camera_heading -= (x - cx) * self.mouse_sensitivity
                self.camera_pitch -= (y - cy) * self.mouse_sensitivity
                self.camera_pitch = max(-90, min(90, self.camera_pitch))
                self.model.setH(self.camera_heading)
                self.game.camera.setP(self.camera_pitch)

        if self.game.ui.is_menu_open:
            return task.cont

        # Расчет вектора движения (в локальных координатах)
        input_vec = Vec3(0, 0, 0)
        
        if inputState.isSet('forward') and self.abilities.is_unlocked("move_forward"):
            input_vec.setY(1)
        if inputState.isSet('backward') and self.abilities.is_unlocked("move_backward"):
            input_vec.setY(-1)
        if inputState.isSet('left') and self.abilities.is_unlocked("move_left"):
            input_vec.setX(-1)
        if inputState.isSet('right') and self.abilities.is_unlocked("move_right"):
            input_vec.setX(1)

        # Гравитация и Поверхность
        self.is_grounded = False
        ground_z = -1000
        ground_normal = Vec3(0, 0, 1) # Default normal
        
        if self.gravity_handler.getNumEntries() > 0:
            self.gravity_handler.sortEntries()
            entry = self.gravity_handler.getEntry(0)
            ground_z = entry.getSurfacePoint(self.game.render).z
            ground_normal = entry.getSurfaceNormal(self.game.render)
            
            if self.model.getZ() - ground_z < 0.1:
                self.is_grounded = True
                self.model.setZ(ground_z)
                self.vertical_velocity = 0

        # Движение с учетом нормали
        if input_vec.length() > 0:
            input_vec.normalize()
            quat = self.model.getQuat()
            global_move = quat.xform(input_vec)
            
            if self.is_grounded:
                d = global_move.dot(ground_normal)
                global_move = global_move - (ground_normal * d)
                global_move.normalize()
            
            self.model.setFluidPos(self.model.getPos() + global_move * self.speed * dt)

        # Прыжок
        if self.is_grounded and inputState.isSet('jump') and self.abilities.is_unlocked("jump"):
            self.vertical_velocity = 12.0
            self.is_grounded = False
            self.model.setZ(self.model.getZ() + 0.1)

        if not self.is_grounded:
            self.vertical_velocity -= 30.0 * dt
            self.model.setFluidZ(self.model.getZ() + self.vertical_velocity * dt)
            
            min_z = self.game.get_terrain_height(self.model.getX(), self.model.getY())
            if self.model.getZ() < min_z:
                self.model.setZ(min_z)
                self.vertical_velocity = 0
                self.is_grounded = True

        self.check_interaction()
        return task.cont

    def check_interaction(self):
        self.hovered_book = None
        if self.picker_handler.getNumEntries() > 0:
            self.picker_handler.sortEntries()
            entry = self.picker_handler.getEntry(0)
            node = entry.getIntoNodePath()
            if node.hasPythonTag("book"):
                self.hovered_book = node.getPythonTag("book")
                self.game.ui.show_interact_prompt(True)
                return
        self.game.ui.show_interact_prompt(False)

    def interact(self):
        if self.hovered_book:
            self.hovered_book.interact()

    def take_damage(self, amount):
        if self.abilities.is_active("shield"): return
        self.health -= amount
        self.game.ui.flash_damage()

    def use_ability_blink(self):
        if self.abilities.use("blink"):
            blink_dist = 15.0
            quat = self.model.getQuat()
            fwd = quat.getForward()
            target_pos = self.model.getPos() + (fwd * blink_dist)
            ground_z = self.game.get_terrain_height(target_pos.x, target_pos.y)
            self.model.setPos(target_pos.x, target_pos.y, ground_z)

    def use_ability_shield(self):
        if self.abilities.use("shield"):
            self.game.ui.show_notification("Shield Activated!")