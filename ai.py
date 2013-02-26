import client
import random
import minesweep
import itertools
import time
import os, sys

DIJ = list(itertools.product((-1, 0, 1), (-1, 0, 1)))
DIJ.remove((0, 0))

WATCH = 1
WATCH_DELAY = 0.1
DEBUG = 0

def get_neigs(pos, field):
    i, j = pos
    return [(i+di, j+dj) for di, dj in DIJ if (i+di, j+dj) in field]

class Timer:
    def __init__(self):
        self.lastTime = time.clock()

    def tick(self):
        curTime = time.clock()
        deltaTime = curTime - self.lastTime
        self.lastTime = curTime
        return int(deltaTime * 1000)

gTimer = Timer()

class Node:
    """
    An uncovered node in the search field
    members:

    pos
    count: how many mines are contained in the rest slots
    restSlots
    """
    # choice count cache
    _cccache = {}

    def __init__(self, pos, count):
        self.pos = pos
        self.count = count
        self.restSlots = set()

    def __repr__(self):
        return 'Node({}, count={}, restSlots={}'.format(
                self.pos, self.count, [slot.pos for slot in self.restSlots])

    def get_choice_count(self):
        n = len(self.restSlots)
        k = self.count
        key = n, k
        value = self._cccache.get(key, None)
        if value is not None:
            return value
        value = sum(1 for t in itertools.product(*((0, 1) for i in range(n))) if sum(t) == k)
        self._cccache[key] = value
        return value

    def get_choices(self):
        slots = list(self.restSlots)
        candidates = []
        for dist in itertools.product(*((0, 1) for i in range(len(slots)))):
            if sum(dist) != self.count: continue
            conflictCount = 0
            if DEBUG: print('<get_choices>')
            for slot, val in zip(slots, dist):
                conflictCount += slot.apply(val)
            for slot in reversed(slots):
                slot.undo()
            if DEBUG: print('</get_choices>')
            candidates.append((conflictCount, list(zip(slots, dist))))
        candidates.sort(key=lambda x:x[0])
        for conflictCount, item in candidates:
            yield item

    def __hash__(self):
        return hash(self.pos)

class Slot:
    """
    An unknown slot in the search field.
    members:
    pos
    val
    nodes: adjacent nodes
    outDated: if is True, then the slot is no longer on field, it became a node
    """
    def __init__(self, pos, nodes):
        self.val = None
        self.pos = pos
        self.nodes = list(nodes)
        self.outDated = False

    def __repr__(self):
        return 'Slot({}, v={}, ns={})'.format(
                self.pos, self.val, [node.pos for node in self.nodes])

    def apply(self, val):
        """
        apply the value and return conflict count.
        """
        assert self.val is None
        self.val = val
        if DEBUG: print('<apply {}, slot={}>'.format(self.pos, self)) 
        for node in self.nodes:
            if DEBUG: print('<remove {} node={}>'.format(node.pos, node))
            node.restSlots.remove(self)
            if val == 1:
                node.count -= 1
            if DEBUG: print('</remove>')
        if DEBUG: print('</apply>')
        return len(self.nodes) - 1

    def add_node(self, node):
        if self.val is not None:
            node.restSlots.remove(self)
            if self.val == 1:
                node.count -= 1
        self.nodes.append(node)

    def undo(self):
        if DEBUG: print('<undo {} slot={}>'.format(self.pos, self))
        for node in self.nodes:
            node.restSlots.add(self)
            if self.val == 1:
                node.count += 1
        self.val = None
        if DEBUG: print('</undo>')

    def __hash__(self):
        return hash(self.pos)

class AIClient(client.Client):
    def __init__(self, game):
        super().__init__(game)
        self.searchField = {p:Slot(p, []) for p in game.positions}
        self.availNodes = set()
        self.safeSlots = []

        self.guessCount = 0
        self.guessProbs = []

        self.mineCount = 0
        self.step = 0

        self.marks = []

    def mark_mine(self, slot):
        slot.apply(1)
        self.mineCount += 1
        self.marks.append(slot)

    def guess(self):
        candidates = []
        for pos, item in self.searchField.items():
            if isinstance(item, Slot) and item.val != 1:
                candidates.append(item)
        self.guessCount += 1
        self.guessProbs.append(-1)
        return random.choice(candidates)

    def search_safe_slot(self):
        self.show("Searching...")
        if DEBUG: print('<search_safe_slot>')
        slots = []
        for slot in self.unknown_active_slots():
            key = sum(node.get_choice_count() for node in slot.nodes)
            slots.append((key, slot))
        slots.sort(key=lambda x: x[0])
        for key, slot in slots:
            slot.apply(1)
            self.mineCount += 1
            found = False
            for solution in self.search([], 1):
                found = True
            self.mineCount -= 1
            slot.undo()
            if not found:
                if DEBUG: print('</search_safe_slot>')
                return slot
        if DEBUG: print('</search_safe_slot>')

    def unknown_active_slots(self):
        for pos, item in self.searchField.items():
            if isinstance(item, Slot):
                slot = item
                if slot.val is None and slot.nodes:
                    yield slot

    def advanced_infer(self):
        self.show("Advanced infering...")
        exist = True
        while exist:
            exist = False
            for slot in self.unknown_active_slots():
                slot.apply(0)
                found = False
                # if no solution found when slot.val = 0, then
                #  slot.val = 1. We can then apply it and try
                #  a simple infer
                for solution in self.search([], 1):
                    found = True
                slot.undo()
                if found: continue
                exist = True
                self.mark_mine(slot)
                slot = self.infer()
                if slot: 
                    return slot

    def search_safe_slot0(self, maxSolCount):
        statistic = {}
        solCount = 0
        for solution in self.search([], maxSolCount):
            solCount += 1
            for slot in solution:
                if slot not in statistic:
                    statistic[slot] = [0, 0]
                statistic[slot][slot.val] += 1
        self.show("solution count: {}".format(solCount))
        for slot, (c0, c1) in statistic.items():
            if c1 == 0:
                self.safeSlots.append(slot)
            if c0 == 0:
                if DEBUG: print('<mine>')
                self.mark_mine(slot)
                if DEBUG: print('</mine>')
        slot = self.get_safe_slot()
        if not slot:
            # still not found, guess the one with minimum possible to have mine
            minProbability = 0.1
            minSlot = None
            for slot, (c0, c1) in statistic.items():
                prob = c1 / (c0 + c1)
                if prob < minProbability:
                    minProbability, minSlot = prob, slot
            slot = minSlot
            if slot:
                self.guessCount += 1
                self.guessProbs.append(minProbability)
        return slot

    def get_input(self):
        slot = None
        while self.marks:
            slot = self.marks.pop()
            if not slot.outDated:
                break
        if slot:
            self.show("step {}".format(self.step))
            if WATCH: time.sleep(WATCH_DELAY)
            return '{} {} {}'.format(self.OPR_MARK, slot.pos[0], slot.pos[1])
        if not self.availNodes:
            # the first step
            i = random.randint(1, game.size[0]-1)
            j = random.randint(1, game.size[1]-1)
            slot = self.searchField[i, j]
        else:
            slot = self.get_safe_slot()

        if not slot:
            # try pick one from safeSlots
            gTimer.tick()
            slot = self.infer()
            self.show("finished in {0:d}ms".format(gTimer.tick()))

        if not slot: 
            # still not found, start search 
            # slot = self.search_safe_slot0(5000)
            gTimer.tick()
            slot = self.search_safe_slot()
            self.show("finished in {0:d}ms".format(gTimer.tick()))

        if not slot:
            # try advanced infer
            gTimer.tick()
            slot = self.advanced_infer()
            self.show("finished in {0:d}ms".format(gTimer.tick()))

        if not slot: 
            # still not found, start search 
            # slot = self.search_safe_slot0(5000)
            gTimer.tick()
            slot = self.search_safe_slot()
            self.show("finished in {0:d}ms".format(gTimer.tick()))
        if not slot:
            # still not found, well, we guess one then.
            slot = self.guess()
        self.step += 1
        self.show("step {}".format(self.step))
        if WATCH: time.sleep(WATCH_DELAY)
        return '{} {} {}'.format(self.OPR_UNCOVER, slot.pos[0], slot.pos[1])

    def get_safe_slot(self):
        while self.safeSlots:
            slot = self.safeSlots.pop()
            if not slot.outDated:
                return slot

    def show_game(self):
        if WATCH: os.system('clear')
        super().show_game()

    def update(self, data):
        """
        data: an iterable, each item is a pair (pos, val)
        """
        super().update(data)
        for pos, val in data:
            if val == self.FLD_MINE: continue
            self.update_field(pos, val)

    def search(self, solution, needCount):
        if DEBUG: print('<search availLen={}>'.format(len(self.availNodes)))
        if not self.availNodes:
            yield solution
        else:
            curCount = 0
            pivot = self.choose_pivot()
            if DEBUG: print('<pivot node={} choices={}>'.format(pivot, pivot.get_choice_count()))
            self.availNodes.remove(pivot)
            for choice in pivot.get_choices():
                for slot, val in choice:
                    slot.apply(val)
                    if slot.val == 1:
                        self.mineCount += 1
                    solution.append(slot)
                try:
                    if self.mineCount <= self.game.mineCount:
                        for solution1 in self.search(solution, needCount):
                            if curCount < needCount:
                                yield solution1
                                curCount += 1
                except RuntimeError as err:
                    self.show("RuntimeError: {}. Avail nodes left: {}".format(err, len(self.availNodes)))
                    print('press enter to continue...')
                    input()
                finally:
                    for slot, val in choice:
                        if slot.val == 1:
                            self.mineCount -= 1
                        slot.undo()
                        solution.pop()
                if curCount >= needCount: break
            self.availNodes.add(pivot)
            if DEBUG: print('</pivot>')
        if DEBUG: print('</search>')

    def update_field(self, pos, count):
        # a slot lie at pos previously
        slot = self.searchField[pos]
        if not isinstance(slot, Slot):
            # updated previously
            return
        if DEBUG: print('<update_field pos={} count={}>'.format(pos, count))
        # apply 0 to the slot
        if slot.val is None:
            slot.apply(0)
        slot.outDated = True
        # replace the slot with a new node
        node = Node(pos, count)
        self.searchField[pos] = node
        # update the neigbour slots
        for pos1 in get_neigs(pos, self.field):
            if isinstance(self.searchField[pos1], Slot):
                slot = self.searchField[pos1]
                node.restSlots.add(slot)
                slot.add_node(node)
        # other stuff
        self.availNodes.add(node)
        if DEBUG: print('</update_field>')

    def infer(self):
        if DEBUG: print('<infer>')
        self.show("Infering...")
        exist = True
        while exist:
            exist = False
            for node in list(self.availNodes):
                if node.get_choice_count() > 1: continue
                self.availNodes.remove(node)
                choice = next(iter(node.get_choices()))
                if DEBUG: print('<choice {}>'.format(choice))
                if choice:
                    exist = True
                for slot, val in choice:
                    if val == 0:
                        slot.apply(0)
                        self.safeSlots.append(slot)
                    else:
                        self.mark_mine(slot)
                if DEBUG: print('</choice>')
                slot = self.get_safe_slot()
                if slot: 
                    if DEBUG: print('</infer>')
                    return slot
        if DEBUG: print('</infer>')

    def choose_pivot(self):
        """
        Choose one pivot from the nodes. The choosed node will be
        the most constrainted then most constraining node.
        """
        bestVal = pivot = None
        for node in self.availNodes:
            a = node.get_choice_count()
            # if a <= 1:
            #     return  node
            b = len(node.restSlots)
            val = -a, b
            if bestVal is None or val > bestVal:
                bestVal, pivot = val, node
        return pivot

if __name__ == '__main__':
    if '-l' in sys.argv[1:]:
        print('load last map')
        game = minesweep.MineSweep.load('last_map')
    else:
        W, H = 35, 80
        count = int(W * H * 0.18)
        game = minesweep.MineSweep((W, H), count)
        game.gen_mines()
        game.save('last_map')
    ai = AIClient(game)
    ai.play()
    print('guess count:', ai.guessCount)
    # print('guesses\' probability:', ai.guessProbs)
