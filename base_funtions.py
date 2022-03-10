"""
basic functions and classes for games
"""
import math
import sys


class Pos:
    """stores a position of a 2d object"""
    def __init__(self, x=0.0, y=0.0):
        self.origin = (x, y)
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return f"x: {self.x}\ny: {self.y}"

    def __getitem__(self, item):
        if item == 0 or item == 'x':
            return self.x
        if item == 1 or item == 'y':
            return self.y

    def move(self, i, j):
        """moves the position a distance"""
        self.x += i
        self.y += j

    def set_pos(self, i, j):
        """sets the position"""
        self.x = i
        self.y = j

    def magnitude(self):
        return math.sqrt(pow(self.x, 2) + pow(self.y, 2))

    def reset(self):
        self.x, self.y = self.origin

    def get_tuple(self):
        return self.x, self.y

    def __complex__(self):
        return complex(self.x, self.y)

    @classmethod
    def from_complex(cls, cmp: complex):
        return cls(cmp.real, cmp.imag)


class Multiplier:
    __slots__ = 'factor'

    def __init__(self, factor):
        self.factor = factor

    def __mul__(self, other):
        return round(self.factor * other)

    def __rmul__(self, other):
        return self.__mul__(other)


if __name__ == '__main__':
    m = Multiplier(1.5)
    print(10 * m)
