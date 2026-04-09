AGES = ['dark', 'feudal', 'castle', 'imperial']
AGE_LABELS = {
    'dark':     'Dark Age',
    'feudal':   'Feudal Age',
    'castle':   'Castle Age',
    'imperial': 'Imperial Age',
}


TEAMS = {
    'blue':   {'color': (60,  120, 220), 'display': 'Blue'},
    'red':    {'color': (220,  50,  50), 'display': 'Red'},
    'green':  {'color': ( 50, 180,  80), 'display': 'Green'},
    'yellow': {'color': (220, 200,  40), 'display': 'Yellow'},
    'purple': {'color': (160,  60, 200), 'display': 'Purple'},
    'teal':   {'color': ( 40, 180, 180), 'display': 'Teal'},
    'orange': {'color': (220, 130,  40), 'display': 'Orange'},
    'pink':   {'color': (220, 120, 180), 'display': 'Pink'},
}


class Player:
    def __init__(self, name, color, team='blue'):
        self.name = name
        self.color = color
        self.team  = team
        self.resources = {"food": 200, "wood": 200, "gold": 200, "stone": 200}
        self.age = 'dark'
        self.units = []
        self.buildings = []

    def add_resource(self, resource, amount):
        if resource in self.resources:
            self.resources[resource] += amount

    def spend_resource(self, resource, amount):
        if self.resources.get(resource, 0) >= amount:
            self.resources[resource] -= amount
            return True
        return False

    def add_unit(self, unit):
        self.units.append(unit)

    def add_building(self, building):
        self.buildings.append(building)
