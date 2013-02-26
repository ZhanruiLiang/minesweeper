import minesweep

class Client:
    STATE_RUNNING = 'running'
    STATE_WIN = 'win'
    STATE_LOST = 'lost'
    OPR_UNCOVER = 'u'
    OPR_MARK = 'm'
    FLD_UNKNOWN = '\u25A1'
    FLD_MINE = 'M'
    FLD_MARK = '\u25A0'
    def __init__(self, game):
        self.game = game

    def play(self):
        game = self.game
        game.start()
        self.field = {p:self.FLD_UNKNOWN for p in game.positions}
        while game.get_state() == self.STATE_RUNNING:
            self.show_game()
            input = self.get_input()
            try:
                opr, i, j = input.split()
                i = int(i)
                j = int(j)
            except ValueError:
                self.show("Invalid input")
                opr = None
            if opr == self.OPR_UNCOVER:
                game.uncover((i, j))
                updatedData = game.get_updated()
                if updatedData is None:
                    self.show("Operation '{}' ignored".format(input))
                else:
                    self.update(updatedData)
                    self.show("Uncovered ({}, {})".format(i, j))
            elif opr == self.OPR_MARK:
                if self.field[i, j] == self.FLD_MARK:
                    self.field[i, j] = self.FLD_UNKNOWN
                elif self.field[i, j] == self.FLD_UNKNOWN:
                    self.field[i, j] = self.FLD_MARK
                else:
                    self.show("Cannot mark there")
            else:
                continue
        state = game.get_state()
        self.show_game()
        if state == self.STATE_WIN:
            self.show("Player win")
        elif state == self.STATE_LOST:
            self.show("Player lost")

    def show_game(self):
        n, m = self.game.size
        print('--'*(m+1))
        print('/ ', end='')
        for j in range(m):
            print(j%10, end='_\n'[j==m-1])
        for i in range(n):
            print('{}|'.format(i % 10), end='')
            for j in range(m):
                val = self.field[i, j]
                c = str(val) if val != 0 else ' '
                print(c, end=' ')
            print()
        print('--'*(m+1))

    def show(self, msg):
        print('message:', msg)

    def get_input(self):
        print('input:', end=' ')
        return input()

    def update(self, data):
        for pos, x in data:
            self.field[pos] = x

if __name__ == '__main__':
    game = minesweep.MineSweep((4, 8), 4)
    game.gen_mines()
    Client(game).play()
