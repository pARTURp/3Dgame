from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, AmbientLight, DirectionalLight, Vec4, Fog
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, GeomVertexFormat, GeomVertexData, Geom, GeomTriangles, GeomNode, GeomVertexWriter
from panda3d.core import BitMask32, CollisionNode, CollisionSphere
from direct.gui.DirectGui import *
import sys
import math
import random
import os

from player import Player
from enemies import EnemyManager
from book import BookManager
from ui import UIManager

# --- НОВОЕ: Класс снаряда ---
class Projectile:
    def __init__(self, game, pos, direction):
        self.game = game
        self.speed = 40.0
        self.lifetime = 3.0
        self.direction = direction
        self.direction.normalize()
        
        self.model = game.loader.loadModel("models/smiley")
        self.model.setScale(0.2)
        self.model.setColor(0, 1, 1, 1) # Cyan color
        self.model.setPos(pos)
        self.model.reparentTo(game.render)
        
        # Коллизия снаряда
        c_node = CollisionNode('projectile')
        c_node.addSolid(CollisionSphere(0, 0, 0, 1))
        c_node.setIntoCollideMask(BitMask32.allOff())
        # Бьет по маске 0 (Враги)
        c_node.setFromCollideMask(BitMask32.bit(0)) 
        
        self.collider = self.model.attachNewNode(c_node)
        self.collider.setPythonTag("projectile", self)
        
        # Мы проверяем попадания вручную в update, чтобы не усложнять хендлеры
        
    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0: return False
        
        self.model.setPos(self.model.getPos() + self.direction * self.speed * dt)
        
        # Простая проверка попаданий по врагам
        for enemy in self.game.enemy_manager.enemies:
            if (enemy.model.getPos() - self.model.getPos()).length() < 1.5:
                enemy.take_damage()
                return False # Снаряд уничтожен
                
        return True

    def destroy(self):
        self.model.removeNode()

class ProceduralTerrain:
    def __init__(self, game, size=256, scale=2.0):
        self.game = game
        self.size = size 
        self.scale = scale 
        self.root = game.render.attachNewNode("Terrain")
        self.generate()
        self.apply_texture() 

    def get_height(self, x, y):
        val = 0
        val += 6.0 * math.sin(x / 15.0) * math.cos(y / 15.0)
        val += 2.0 * math.sin(x / 5.0 + y / 5.0)
        
        dist_sq = x*x + y*y
        if dist_sq < 100:
            val *= (dist_sq / 100.0)
        return val

    def generate(self):
        format = GeomVertexFormat.getV3n3t2()
        vdata = GeomVertexData('terrain', format, Geom.UHStatic)
        
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        texcoord = GeomVertexWriter(vdata, 'texcoord')
        
        offset = (self.size * self.scale) / 2
        
        for y in range(self.size):
            for x in range(self.size):
                px = (x * self.scale) - offset
                py = (y * self.scale) - offset
                pz = self.get_height(px, py)
                
                vertex.addData3(px, py, pz)
                normal.addData3(0, 0, 1)
                texcoord.addData2(x / 10.0, y / 10.0)

        prim = GeomTriangles(Geom.UHStatic)
        
        for y in range(self.size - 1):
            for x in range(self.size - 1):
                v1 = y * self.size + x
                v2 = y * self.size + (x + 1)
                v3 = (y + 1) * self.size + (x + 1)
                v4 = (y + 1) * self.size + x
                
                prim.addVertices(v1, v2, v3)
                prim.addVertices(v1, v3, v4)
                
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        node = GeomNode('TerrainMesh')
        node.addGeom(geom)
        
        self.mesh_np = self.root.attachNewNode(node)
        self.mesh_np.setCollideMask(BitMask32.bit(2))

    def apply_texture(self):
        if os.path.exists("textures/floor.png"):
            try:
                tex = self.game.loader.loadTexture("textures/floor.png")
                self.mesh_np.setTexture(tex)
                self.mesh_np.setColor(1, 1, 1, 1)
            except:
                self.mesh_np.setColor(0.3, 0.5, 0.3)
        else:
            self.mesh_np.setColor(0.3, 0.5, 0.3)

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        props = WindowProperties()
        props.setTitle("The Void of Ignorance")
        props.setCursorHidden(False)
        self.win.requestProperties(props)
        
        self.cTrav = CollisionTraverser()
        self.pusher = CollisionHandlerPusher()
        
        self.ui = UIManager(self)
        self.ui.show_main_menu(self.start_game)
        self.is_game_running = False
        
        self.projectiles = [] # Список снарядов

    def start_game(self):
        self.ui.hide_all_menus()
        
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)
        self.is_game_running = True

        self.setup_environment()
        
        self.player = Player(self)
        self.book_manager = BookManager(self)
        self.enemy_manager = EnemyManager(self)
        
        self.ui.setup_game_ui(self.player)

        self.book_manager.start_spawning()
        self.enemy_manager.start_spawning()
        self.taskMgr.add(self.update, "MainUpdate")

    def setup_environment(self):
        self.terrain = ProceduralTerrain(self)
        
        self.skybox = self.loader.loadModel("models/box")
        self.skybox.setScale(500)
        self.skybox.setBin('background', 0)
        self.skybox.setDepthWrite(False)
        self.skybox.setLightOff()
        self.skybox.reparentTo(self.render)

        if os.path.exists("textures/skybox.jpg"):
            try:
                sky_tex = self.loader.loadTexture("textures/skybox.jpg")
                self.skybox.setTexture(sky_tex)
                self.skybox.setColor(1, 1, 1, 1)
            except:
                self.skybox.setColor(0.1, 0.1, 0.15, 1)
        else:
            self.skybox.setColor(0.1, 0.1, 0.15, 1)

        alight = AmbientLight('alight')
        alight.setColor(Vec4(0.4, 0.4, 0.5, 1))
        self.render.setLight(self.render.attachNewNode(alight))

        dlight = DirectionalLight('dlight')
        dlight.setColor(Vec4(0.8, 0.8, 0.7, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0)
        self.render.setLight(dlnp)
        
        myFog = Fog("WorldFog")
        myFog.setColor(0.1, 0.1, 0.15)
        myFog.setExpDensity(0.01)
        self.render.setFog(myFog)

    def get_terrain_height(self, x, y):
        if hasattr(self, 'terrain'):
            return self.terrain.get_height(x, y)
        return 0.0

    # --- НОВОЕ: Спавн снаряда ---
    def spawn_projectile(self, pos, direction):
        p = Projectile(self, pos, direction)
        self.projectiles.append(p)

    def update(self, task):
        if not self.is_game_running: return task.cont
        if hasattr(self, 'skybox'): 
            self.skybox.setPos(self.camera.getPos())
        
        if self.player.health <= 0:
            self.game_over()
            return task.done

        # --- НОВОЕ: Обновление снарядов ---
        active_projs = []
        for p in self.projectiles:
            if p.update(globalClock.getDt()):
                active_projs.append(p)
            else:
                p.destroy()
        self.projectiles = active_projs

        self.ui.update(globalClock.getDt())
        return task.cont

    def game_over(self):
        self.is_game_running = False
        props = WindowProperties()
        props.setCursorHidden(False)
        props.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(props)
        self.ui.show_game_over()
        
    def exit_to_menu(self):
        self.is_game_running = False
        self.taskMgr.remove("MainUpdate")
        self.taskMgr.remove("PlayerUpdate")
        self.taskMgr.remove("EnemySpawn")
        self.taskMgr.remove("BookSpawn")
        self.taskMgr.remove("InitialUnlock")
        
        if hasattr(self, 'player'): self.player.cleanup()
        if hasattr(self, 'enemy_manager'): self.enemy_manager.cleanup()
        if hasattr(self, 'book_manager'): self.book_manager.cleanup()
        if hasattr(self, 'terrain'): self.terrain.root.removeNode()
        if hasattr(self, 'skybox'): self.skybox.removeNode()
        
        for p in self.projectiles: p.destroy()
        self.projectiles = []
        
        props = WindowProperties()
        props.setCursorHidden(False)
        props.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(props)
        self.ui.show_main_menu(self.start_game)

game = Game()
game.run()
