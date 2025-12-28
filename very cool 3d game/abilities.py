import time

class AbilitySystem:
    def __init__(self):
        self.abilities = {
            # --- БАЗОВЫЕ ДВИЖЕНИЯ ---
            "move_forward": {
                "name": "Move Forward",
                "description": "Your legs respond. You can walk forward.",
                "type": "passive",
                "unlocked": False
            },
            "move_backward": {
                "name": "Move Backward",
                "description": "You can step back from danger.",
                "type": "passive",
                "unlocked": False
            },
            "move_left": {
                "name": "Step Left",
                "description": "Sidestep to the left.",
                "type": "passive",
                "unlocked": False
            },
            "move_right": {
                "name": "Step Right",
                "description": "Sidestep to the right.",
                "type": "passive",
                "unlocked": False
            },
            "jump": {
                "name": "Jump",
                "description": "Defy gravity briefly.",
                "type": "passive",
                "unlocked": False
            },
            # --- НОВОЕ: АТАКА ---
            "shoot": {
                "name": "Void Bolt",
                "description": "Fire projectiles of raw energy.",
                "type": "passive", 
                "unlocked": False
            },
            
            # --- АКТИВНЫЕ СПОСОБНОСТИ ---
            "blink": {
                "name": "Blink",
                "description": "Teleport forward instantly.",
                "type": "active",
                "cooldown": 10.0,
                "duration": 0.0,
                "last_used": 0.0,
                "active": False,
                "unlocked": False,
                "icon": "blink_icon"
            },
            "shield": {
                "name": "Divine Shield",
                "description": "Invulnerability for 5 seconds.",
                "type": "active",
                "cooldown": 20.0,
                "duration": 5.0,
                "last_used": 0.0,
                "active": False,
                "unlocked": False,
                "icon": "shield_icon"
            }
        }
    
    def is_unlocked(self, name):
        return self.abilities.get(name, {}).get("unlocked", False)

    def can_use(self, name):
        now = time.time()
        ability = self.abilities.get(name)
        if not ability: return False
        if not ability.get("unlocked", False): return False
        if ability.get("type") == "passive": return True
        return (now - ability["last_used"]) >= ability["cooldown"]

    def use(self, name):
        if self.can_use(name):
            self.abilities[name]["last_used"] = time.time()
            if self.abilities[name]["duration"] > 0:
                self.abilities[name]["active"] = True
            return True
        return False

    def is_active(self, name):
        ability = self.abilities.get(name)
        if not ability or not ability.get("active", False):
            return False
        if time.time() - ability["last_used"] > ability["duration"]:
            ability["active"] = False
            return False
        return True