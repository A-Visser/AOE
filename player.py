class Player:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.resources = {"food": 200, "wood": 200, "gold": 0, "stone": 0}
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
