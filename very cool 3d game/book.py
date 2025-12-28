from panda3d.core import CollisionNode, CollisionBox, BitMask32
import random
import math

class Book:
    def __init__(self, game, pos):
        self.game = game
        self.model = game.loader.loadModel("models/box")
        self.model.setScale(0.4, 0.5, 0.1)
        self.model.setColor(0.8, 0.7, 0.3, 1) # Золотой цвет
        
        z = self.game.get_terrain_height(pos[0], pos[1]) + 0.2
        self.model.setPos(pos[0], pos[1], z)
        self.model.setH(random.uniform(0, 360))
        self.model.setP(random.uniform(-5, 5))
        self.model.reparentTo(game.render)
        
        # Интерактивный узел - Bit 1
        self.interact_node = self.model.attachNewNode(CollisionNode('book_interact'))
        self.interact_node.node().addSolid(CollisionBox((0,0,0), 0.5, 0.5, 0.5))
        self.interact_node.node().setIntoCollideMask(BitMask32.bit(1)) 
        self.interact_node.setPythonTag("book", self)

    def interact(self):
        unlocked_name = self.game.player.unlock_random_ability()
        self.game.book_manager.books.remove(self)
        self.cleanup()
        self.game.ui.show_notification(f"Unlocked: {unlocked_name}")

    def cleanup(self):
        self.model.removeNode()

class BookManager:
    def __init__(self, game):
        self.game = game
        self.books = []
        self.max_books = 30 
        self.spawn_timer = 0

    def start_spawning(self):
        # 1. Сначала спавним 6 книг в ряд перед игроком для теста
        self.spawn_debug_row()
        # 2. Затем заполняем остальную карту до лимита
        self.spawn_initial()
        self.game.taskMgr.add(self.update, "BookSpawn")

    def spawn_debug_row(self):
        """Создает 6 книг в ряд перед игроком (X=0, Y=5..15)"""
        for i in range(8):
            x = (i - 2.5) * 2 # Расставляем по горизонтали
            y = 10            # В 10 метрах перед спавном
            book = Book(self.game, (x, y))
            self.books.append(book)

    def spawn_initial(self):
        while len(self.books) < self.max_books:
            self.spawn_one()

    def spawn_one(self):
        x = random.uniform(-120, 120)
        y = random.uniform(-120, 120)
        book = Book(self.game, (x, y))
        self.books.append(book)

    def update(self, task):
        dt = globalClock.getDt()
        
        if len(self.books) < self.max_books:
            self.spawn_timer += dt
            if self.spawn_timer > 10.0:
                self.spawn_timer = 0
                self.spawn_one()
        else:
            self.spawn_timer = 0
                
        return task.cont

    def cleanup(self):
        for b in self.books:
            b.cleanup()
        self.books = []