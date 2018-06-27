import sys
import math
import collections
import random

yells_occurred = {}
            
def begin():
    width = int(input())
    height = int(input())
    data = [input() for _ in range(height)]
    world = World(width, height, data)
    
    sanity_loss_lonely, sanity_loss_group, wanderer_spawn_time, wanderer_life_time = [int(i) for i in input().split()]
    
    while True:
        reset()
        entity_count = int(input())  # the first given entity corresponds to your explorer
        entities = []
        for i in range(entity_count):
            entity_type, id, x, y, param_0, param_1, param_2 = [int(d) if i > 0 else d for i, d in enumerate(input().split())]
            entity = Entity(entity_type, id, x, y, param_0, param_1, param_2)
            if entity.isExplorer():
                if entity.entity_id not in yells_occurred:
                    yells_occurred[entity.entity_id] = []
                entity.yelled_players = yells_occurred[entity.entity_id]
            if entity.isYellEffect() and entity.getYelledPlayer() not in yells_occurred[entity.getEffectOwner()]:
                yells_occurred[entity.getEffectOwner()].append(entity.getYelledPlayer())
            if entity.isLightEffect():
                owners = [x for x in entities if entity.getEffectOwner() == x.entity_id]
                if owners:
                    owners[0].hasLight = True
            if entity.isPlanEffect():
                owners = [x for x in entities if entity.getEffectOwner() == x.entity_id]
                if owners:
                    owners[0].hasPlan = True
            entities.append(entity)
            
            log(entity)
            #if entity.isExplorer():
            #    log(entity.yelled_players)
        
        #log(yells_occurred)
        
        my_explorer = entities[0]
        
        #execute("WAIT")
        move_decision = Functions.getMoveDecision(world, entities, my_explorer)
        execute(move_decision)
    
class World:
    def __init__(self, w, h, d):
        self.width = w
        self.height = h
        self.size = w * h
        self.world = [None for _ in range(self.size)]
        for i, line in enumerate(d):
            self._setRow(i, line)
        self._get_dist_map()
        self._getDeadEndCells()
            
    def isWalkable(self, x, y):
        if 0 < x < self.width and 0 < y < self.height:
            index = self._coordToIndex(x, y)
            return self._isWalkable(index)
        return False
        
    def isDeadEnd(self, x, y):
        if 0 < x < self.width and 0 < y < self.height:
            index = self._coordToIndex(x, y)
            return self._isDeadEnd(index)
        return False
        
    def getNeighbors(self, x, y, origin=False):
        neighbors = []
        for dx, dy in [(-1, 0), (0, 1), (1, 0), (0, -1)]:
            neighbor = (x + dx, y + dy)
            #make sure this neighbor is walkable
            if not self.isWalkable(neighbor[0], neighbor[1]):
                continue
            neighbors.append(neighbor)
        if origin:
            neighbors.append((x, y))
        return neighbors
        
    def getDistance(self, x1, y1, x2, y2):
        try:
            return self._dist_map[((x1, y1), (x2, y2))]
        except KeyError:
            return 10000, (x1, y1)
            
    def getPath(self, x1, y1, x2, y2):
        start = (x1, y1)
        end = (x2, y2)
        cell = start
        path = []
        
        while cell != end:
            path.append(cell)
            cell = self.getDistance(cell[0], cell[1], end[0], end[1])[1]
        
        path.append(end)
        
        return path
            
    def hasLineOfSight(self, x1, y1, x2, y2):
        #must have either same xs or same ys
        if x1 != x2 and y1 != y2:
            return False
        #make sure x1/y1 < x2/y2. swap if necessary
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        #return the predicate that all cells between x1, y1 -> x2, y2 are walkable
        return all(self.isWalkable(x, y) for x in range(x1, x2+1) for y in range(y1, y2+1))
            
    def getWalkableCells(self):
        return [x for x in range(self.size) if self._isWalkable(x)]
        
    def getWalkableCellCoords(self):
        return [self._indexToCoord(x) for x in self.getWalkableCells()]
        
    def getWandererSpawns(self):
        return [i for i, d in enumerate(self.world) if d.lower() == "w"]
        
    def getWandererSpawnCoords(self):
        return [self._indexToCoord(x) for x in self.getWandererSpawns()]
        
    def getShelters(self):
        return [i for i, d in enumerate(self.world) if d.lower() == "u"]
        
    def getShelterCoords(self):
        return [self._indexToCoord(x) for x in self.getShelters()]
    
    def _getDeadEndCells(self):
        to_process = collections.deque([c for c in self.getWalkableCells() if len(self._getNeighbors(c)) == 1])
        dead_end_cells = []
        
        while to_process:
            cell = to_process.popleft()
            
            neighbors = self._getNeighbors(cell)
            if len(neighbors) <= 2:
                for neighbor in neighbors:
                    if neighbor not in dead_end_cells:
                        to_process.append(neighbor)
                
                dead_end_cells.append(cell)
        
        #store this in variable
        self._dead_end_cells = dead_end_cells
        log(sorted([self._indexToCoord(i) for i in self._dead_end_cells]))
        
    def _isWalkable(self, index):
        if 0 < index < self.size:
            return self.world[index] not in ['#']
        return False
        
    def _isDeadEnd(self, index):
        return index in self._dead_end_cells
        
    def _getNeighbors(self, index, origin=False):
        coords = self._indexToCoord(index)
        return [self._coordToIndex(c[0], c[1]) for c in self.getNeighbors(coords[0], coords[1], origin=origin)]
            
    def _get_dist_map(self):
        #store the distance between a pair of coords
        master_dist_map = {}
        
        #list of walkable tiles to start from
        for start_tile in self.getWalkableCellCoords():
            #create a map of distances from start_tile
            dist_map = {}
            dist_map[start_tile] = 0
            cell_from = {}
            cell_from[start_tile] = start_tile
            #create a queue of tiles to process, start with start_tile
            tiles = collections.deque()
            tiles.append(start_tile)
            #while we have tiles to process
            while tiles:
                #pop one, find the unprocessed neighbors, calculate distance
                tile = tiles.popleft()
                for neighbor in self.getNeighbors(tile[0], tile[1]):
                    if neighbor in dist_map:
                        continue
                    #neighbor distance is current distance plus 1
                    dist_map[neighbor] = dist_map[tile] + 1
                    cell_from[neighbor] = tile
                    #add neighbor to process next 
                    tiles.append(neighbor)
            
            #store the distance here
            for c, d in dist_map.items():
                #master_dist_map[(start_tile, c)] = d
                master_dist_map[(c, start_tile)] = (d, cell_from[c])
                
        self._dist_map = master_dist_map
        #Display test routes
        #for _ in range(10):
        #    x_1 = random.randint(0, self.width)
        #    y_1 = random.randint(0, self.height)
        #    x_2 = random.randint(0, self.width)
        #    y_2 = random.randint(0, self.height)
        #    d = self.getDistance(x_1, y_1, x_2, y_2)
        #    log("{:1s}({:2d}, {:2d}) -> {:1s}({:2d}, {:2d}) = {:2s} ({:2d}, {:2d})".format("" if self.isWalkable(x_1, y_1) else "!", x_1, y_1, "" if self.isWalkable(x_2, y_2) else "!", x_2, y_2, "##" if d[0] == 10000 else str(d[0]), d[1][0], d[1][1]))
        
    def _indexToCoord(self, i):
        return i % self.width, i // self.width
        
    def _coordToIndex(self, x, y):
        return y * self.width + x
        
    def _setRow(self, y, data):
        assert type(data) == str, "Data must be a string type: " + str(data)
        for x, d in enumerate(data):
            index = self._coordToIndex(x, y)
            self.world[index] = d
            
class Entity:
    def __init__(self, t, i, x, y, p1, p2, p3):
        self.entity_type = t
        self.entity_id = i
        self.x = x
        self.y = y
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3
        self.hasLight = False
        self.hasPlan = False
        self.yelled_players = []
        
    def isExplorer(self):
        return self.entity_type.lower() == "explorer"
        
    def isEffect(self):
        return any([self.isPlanEffect(), self.isLightEffect(), self.isShelterEffect(), self.isYellEffect()])
    
    def isPlanEffect(self):
        return self.entity_type.lower() == "effect_plan"
        
    def isLightEffect(self):
        return self.entity_type.lower() == "effect_light"
        
    def isShelterEffect(self):
        return self.entity_type.lower() == "effect_shelter"
        
    def isYellEffect(self):
        return self.entity_type.lower() == "effect_yell"
        
    def isMinion(self):
        return any([self.isWanderer(), self.isSlasher()])
    
    def isWanderer(self):
        return self.entity_type.lower() == "wanderer"
    
    def isSlasher(self):
        return self.entity_type.lower() == "slasher"
        
    def getSanity(self):
        assert self.isExplorer(), "{}:{} does not have sanity.".format(self.entityType, self.entity_id)
        return self.p1
        
    def isSpawning(self):
        assert self.isMinion(), "{}:{} is not able to spawn".format(self.entityType, self.entity_id)
        return self.p2 == 0
        
    def isWandering(self):
        assert self.isMinion(), "{}:{} is not able to wander".format(self.entityType, self.entity_id)
        return self.p2 == 1
        
    def isStalking(self):
        assert self.isMinion(), "{}:{} is not able to stalk".format(self.entityType, self.entity_id)
        return self.p2 == 2
        
    def isRushing(self):
        assert self.isMinion(), "{}:{} is not able to rush".format(self.entityType, self.entity_id)
        return self.p2 == 3
        
    def isStunned(self):
        assert self.isMinion(), "{}:{} is not able to be stunned".format(self.entityType, self.entity_id)
        return self.p2 == 4
        
    def getEffectOwner(self):
        assert self.isEffect(), "{}:{} does not have an effect owner".format(self.entityType, self.entity_id)
        return self.p2
        
    def getTimeBeforeSpawn(self):
        assert self.isMinion() and self.isSpawning(), "{}:{} does not have a time before spawn.".format(self.entityType, self.entity_id)
        return self.p1
        
    def getTimeBeforeRecall(self):
        assert self.isWanderer() and not self.isSpawning(), "{}:{} does not have a time before recall.".format(self.entityType, self.entity_id)
        return self.p1
        
    def getTimeBeforeChangingState(self):
        assert self.isSlasher(), "{}:{} does not have a time before changing state".format(self.entityType, self.entity_id)
        return self.p1
        
    def getRemainingShelterEnergy(self):
        assert self.isShelterEffect(), "{}:{} does not have remaining energy".format(self.entityType, self.entity_id)
        return self.p1
    
    def getRemainingEffectTime(self):
        assert self.isEffect(), "{}:{} does not have remaining effect time".format(self.entityType, self.entity_id)
        return self.p1
        
    def getRemainingLights(self):
        assert self.isExplorer(), "{}:{} does not have lights".format(self.entityType, self.entity_id)
        return self.p3
        
    def getRemainingPlans(self):
        assert self.isExplorer(), "{}:{} does not have plans".format(self.entityType, self.entity_id)
        return self.p2
    
    def getYelledPlayer(self):
        assert self.isYellEffect(), "{}:{} does not have a yelled player".format(self.entityType, self.entity_id)
        return self.p3
        
    def getTargetedExplorer(self):
        assert self.isMinion(), "{}:{} does not have a target.".format(self.entityType, self.entity_id)
        return self.p3
        
    def __str__(self):
        return "{:14s}: {:3d} ( {:2d}, {:2d} ) [ {:3d} {:3d} {:3d} ]".format(self.entity_type, self.entity_id, self.x, self.y, self.p1, self.p2, self.p3)
    
class Functions:
    def getEntitiesAt(world, entities, x, y, steps=0, radius=0):
        assert steps*radius == 0, "Must either specify steps or radius, not both"
        if steps > 0:
            return [e for e in entities if world.getDistance(e.x, e.y, x, y)[0] <= steps]
        elif radius > 0:
            return [e for e in entities if abs(e.x-x) + abs(e.y-y) <= radius]
        else:
            return [e for e in entities if e.x==x and e.y==y]
        
    def getMoveDecision(world, entities, my_explorer):
        my_neighbor_cells = world.getNeighbors(my_explorer.x, my_explorer.y, origin=True)
        other_explorers = [e for e in entities if e.isExplorer() and e is not my_explorer]
        minions = [m for m in entities if m.isMinion()]
        wanderers = [w for w in minions if w.isWanderer()]
        wanderers_targeting_me = [w for w in wanderers if w.getTargetedExplorer() == my_explorer.entity_id]
        wanderers_not_targeting_me = [w for w in wanderers if not w.isSpawning() and w not in wanderers_targeting_me]
        
        slashers = [s for s in minions if s.isSlasher()]
        effects = [e for e in entities if e.isEffect()]
        shelters = [s for s in effects if s.isShelterEffect()]
        
        move_options = {n: 0 for n in my_neighbor_cells}
        
        for neighbor in my_neighbor_cells:
            for wanderer in wanderers:
                if world.getDistance(neighbor[0], neighbor[1], wanderer.x, wanderer.y)[0] <= 1:
                    move_options[neighbor] -= 1000
            for wanderer in wanderers_targeting_me:
                current_distance = world.getDistance(my_explorer.x, my_explorer.y, wanderer.x, wanderer.y)[0]
                anticipated_new_wanderer_location = world.getDistance(wanderer.x, wanderer.y, neighbor[0], neighbor[1])[1]
                anticipated_new_distance = world.getDistance(neighbor[0], neighbor[1], anticipated_new_wanderer_location[0], anticipated_new_wanderer_location[1])[0]
                if anticipated_new_distance < current_distance:
                    move_options[neighbor] -= 100
            for wanderer in wanderers_not_targeting_me:
                target = [e for e in other_explorers if e.entity_id == wanderer.getTargetedExplorer()]
                if target:
                    target = target[0]
                    for other_neighbor in world.getNeighbors(target.x, target.y):
                        anticipated_new_wanderer_location = world.getDistance(wanderer.x, wanderer.y, other_neighbor[0], other_neighbor[1])[1]
                        anticipated_new_distance_to_target = world.getDistance(other_neighbor[0], other_neighbor[1], anticipated_new_wanderer_location[0], anticipated_new_wanderer_location[1])[0]
                        anticipated_new_distance_to_me = world.getDistance(anticipated_new_wanderer_location[0], anticipated_new_wanderer_location[1], neighbor[0], neighbor[1])[0]
                        if anticipated_new_distance_to_me < anticipated_new_distance_to_target:
                            move_options[neighbor] -= 10
        
            for slasher in slashers:
                if slasher.isSpawning():
                    pass
                elif slasher.isWandering():
                    if world.hasLineOfSight(slasher.x, slasher.y, neighbor[0], neighbor[1]):
                        move_options[neighbor] -= 20
                elif slasher.isStalking():
                    if world.hasLineOfSight(slasher.x, slasher.y, neighbor[0], neighbor[1]):
                        move_options[neighbor] -= 50
                elif slasher.isRushing():
                    if world.hasLineOfSight(slasher.x, slasher.y, neighbor[0], neighbor[1]):
                        move_options[neighbor] -= 100
                elif slasher.isStunned():
                    pass
                
        #visualize move options:
        coord_u = (my_explorer.x, my_explorer.y-1)
        coord_d = (my_explorer.x, my_explorer.y+1)
        coord_l = (my_explorer.x-1, my_explorer.y)
        coord_r = (my_explorer.x+1, my_explorer.y)
        coord_c = (my_explorer.x, my_explorer.y)
        log("{:^5s} {:^5s} {:^5s}".format("", str(move_options[coord_u]) if coord_u in move_options else "#####", ""))
        log("{:^5s} {:^5s} {:^5s}".format(str(move_options[coord_l]) if coord_l in move_options else "#####", str(move_options[coord_c]) if coord_c in move_options else "#####", str(move_options[coord_r]) if coord_r in move_options else "#####"))
        log("{:^5s} {:^5s} {:^5s}".format("", str(move_options[coord_d]) if coord_d in move_options else "#####", ""))
        
        move_scores = list(move_options.items())
        move_scores.sort(key=lambda x: x[1], reverse=True)
        
        if move_scores:
            best_move = move_scores[0][0]
            best_score = move_scores[0][1]
            if best_move != coord_c and best_score != move_options[coord_c]: #and any(x[1] < 30 for x in move_scores): #If no values are very negative, then there is not an active threat
                return "MOVE {} {}".format(best_move[0], best_move[1])
        
        return "WAIT"
                
def log(msg):
    print(str(msg), file=sys.stderr)

def execute(cmd):
    global executed
    if not executed:
        print(cmd)
    executed = True

def reset():
    global executed
    executed = False

begin()