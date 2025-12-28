from panda3d.core import CollisionNode, CollisionSphere, BitMask32, Vec3
import random
import os
import math

class Enemy:
    def __init__(self, game, pos, speed):
        self.game = game
        self.speed = speed
        
        # Логика поведения
        self.chase_radius = 40.0
        self.attack_range = 2.0
        self.attack_cooldown = 1.5
        self.attack_timer = 0
        
        self.model = game.loader.loadModel("models/smiley")
        self.model.setScale(1)
        self.model.reparentTo(game.render)
        
        z = self.game.get_terrain_height(pos[0], pos[1]) + 1.0
        self.model.setPos(pos[0], pos[1], z)
        
        # Текстура врага
        if os.path.exists("textures/enemy.png"):
            try:
                tex = game.loader.loadTexture("textures/enemy.png")
                self.model.setTexture(tex, 1)
                self.model.setColor(1, 1, 1, 1) # Белый, чтобы текстура была видна
            except:
                self.model.setColor(1, 0, 0, 1) # Красный если ошибка
        else:
            self.model.setColor(1, 0, 0, 1) # Красный если нет файла

        # Коллизия
        self.collider = self.model.attachNewNode(CollisionNode('enemy'))
        self.collider.node().addSolid(CollisionSphere(0, 0, 0, 1.2))
        self.collider.node().setFromCollideMask(BitMask32.allOff()) 
        # Бит 0 (Враги/Стены)
        self.collider.node().setIntoCollideMask(BitMask32.bit(0))
        
        # --- НОВОЕ: Чтобы работать с update logic ---
        self.collider.setPythonTag("enemy", self)

    def update(self, player_node, dt):
        if not player_node: return
        
        if self.attack_timer > 0:
            self.attack_timer -= dt
            
        current_pos = self.model.getPos()
        player_pos = player_node.getPos()
        dist_to_player = (player_pos - current_pos).length()

        # Преследование только если близко
        if dist_to_player <= self.chase_radius:
            direction = player_pos - current_pos
            direction.setZ(0)
            if direction.length() > 0.001:
                direction.normalize()
                
            self.model.headsUp(player_pos)
            self.model.setP(0); self.model.setR(0)

            if dist_to_player > self.attack_range:
                # Движение
                new_pos = current_pos + (direction * self.speed * dt)
                # Привязка к рельефу
                terrain_z = self.game.get_terrain_height(new_pos.x, new_pos.y)
                self.model.setPos(new_pos.x, new_pos.y, terrain_z + 1.0)
            
            else:
                # Атака (Удар по таймеру)
                if self.attack_timer <= 0:
                    self.attack_timer = self.attack_cooldown
                    self.game.player.take_damage(15)
                    self.model.setZ(self.model.getZ() + 0.5) # Визуальный "прыжок" при ударе
    
    # --- НОВОЕ: Получение урона ---
    def take_damage(self):
        # Для простоты - умирают с одного удара
        self.cleanup()
        if self in self.game.enemy_manager.enemies:
            self.game.enemy_manager.enemies.remove(self)

    def cleanup(self):
        self.model.removeNode()

class EnemyManager:
    def __init__(self, game):
        self.game = game
        self.enemies = []
        self.base_speed = 4.0
        self.current_speed = 4.0
        self.spawn_timer = 0
        self.max_enemies = 15

    def set_difficulty(self, speed_mult):
        self.current_speed = self.base_speed * speed_mult
            
    def start_spawning(self):
        self.game.taskMgr.add(self.update, "EnemySpawn")

    def update(self, task):
        dt = globalClock.getDt()
        self.spawn_timer += dt
        
        # Спавн чуть чаще, карта большая
        if self.spawn_timer > 3.0 and len(self.enemies) < self.max_enemies:
            self.spawn_timer = 0
            angle = random.uniform(0, 3.14 * 2)
            dist = random.uniform(30, 80) # Враги появляются вокруг игрока
            p_pos = self.game.player.model.getPos()
            
            x = p_pos.x + math.cos(angle) * dist
            y = p_pos.y + math.sin(angle) * dist
            
            # Лимит карты +/- 120
            x = max(-120, min(120, x))
            y = max(-120, min(120, y))
            
            enemy = Enemy(self.game, (x, y, 0), self.current_speed)
            self.enemies.append(enemy)

        if hasattr(self.game, 'player') and self.game.player:
            # Создаем копию списка, так как враги могут удаляться в процессе (смерть)
            for e in self.enemies[:]:
                e.update(self.game.player.model, dt)
            
        return task.cont

    def cleanup(self):
        for e in self.enemies:
            e.cleanup()
        self.enemies = []