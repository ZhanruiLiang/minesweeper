import random
import itertools
import pickle

def shuffle(lst):
    n = len(lst)
    for k in range(20):
        for i in range(n):
            for j in range(n):
                if (1+i+j+k)*(7+i-j+k) % 3:
                    lst[i], lst[j] = lst[j], lst[i]

class MineSweep:
    """
    members:

    mines: a set of positions that has a mine.
    neigs: a dict of position to list. For example, neigsCounts[p] = [p1, p2, p3].
    uncovered: a set of uncovered positions.
    positions: a set of valid positions.

    methods:
    uncover(pos)
    start()
    get_updated()
    get_state()
    """
    def __init__(self, size, mineCount):
        self.size = w, h =size
        self.mineCount = mineCount
        if mineCount > w * h:
            raise Exception("field with size {}x{} can not hold {} mines".format(w, h, mineCount))
        self.state = 'not_start'
        self.positions = {(i, j) for i in range(self.size[0]) for j in range(self.size[1])}
        self.neigs = {p:self.get_neigs(p) for p in self.positions}
        self.mines = None

    def gen_mines(self):
        mines = list(self.positions)
        # shuffle(mines)
        random.shuffle(mines)
        self.mines = set(mines[:self.mineCount])

    def start(self):
        """
        Start the game play
        """
        assert self.mines
        positions = self.positions
        self.uncovered = set()

        self.neigMineCount = {}
        for p in positions:
            self.neigMineCount[p] = sum(1 for p1 in self.neigs[p] if p1 in self.mines)
        self.state = 'running'

    def get_neigs(self, pos):
        D = itertools.product(range(-1, 2), range(-1, 2))
        i, j = pos
        neigs = []
        for di, dj in D:
            if di == 0 and dj == 0: continue
            i1, j1 = i + di, j + dj
            if (i1, j1) in self.positions:
                neigs.append((i1, j1))
        return neigs

    def uncover(self, pos):
        """
        Uncover a position. User can then call get_updated to get results.
        """
        if self.state != 'running':
            self.updated = None
            return
        if pos not in self.positions or pos in self.uncovered:
            self.updated = None
            return
        self.updated = updated = []
        if pos in self.mines:
            for p in self.positions:
                if p in self.mines:
                    x = 'M'
                else:
                    x = self.neigMineCount[p]
                updated.append((p, x))
            self.state = 'lost'
            return

        stk = [pos]
        self.uncovered.add(pos)
        while stk:
            p0 = stk.pop()
            updated.append((p0, self.neigMineCount[p0]))
            if self.neigMineCount[p0] == 0:
                for p1 in self.neigs[p0]:
                    if p1 not in self.uncovered and p1 not in self.mines:
                        stk.append(p1)
                        self.uncovered.add(p1)

        if len(self.uncovered) + len(self.mines) == len(self.positions):
            self.state = 'win'

    def get_updated(self):
        """
        Get last updated stuff. If success, return a list of updated (position
        , count) pair. Return None if last operation is invalid.
        """
        updated, self.updated = self.updated, None
        return updated

    def get_state(self):
        """
        return current game state. A game state is one of the following:
        * not_start
        * running
        * lost
        * win
        """
        return self.state

    def save(self, filename):
        with open(filename, 'wb') as outfile:
            pickle.dump(self, outfile)

    @staticmethod
    def load(filename):
        with open(filename, 'rb') as infile:
            data = pickle.load(infile)
        return data
