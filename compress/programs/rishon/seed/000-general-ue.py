"""SUMMARY: the reference circuit of the rishon encoding (UE) expressed through the Builder; every angle is a linear function of spec.alpha / spec.beta.

"""
FAMILY = 'seed'
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    b = Builder(spec)
    b.cx(0, 1)
    b.p(-0.75 * spec.alpha, 1)
    b.cx(0, 1)
    b.cx(4, 5)
    b.p(-0.75 * spec.alpha, 5)
    b.cx(4, 5)
    b.cx(8, 9)
    b.p(-0.75 * spec.alpha, 9)
    b.cx(8, 9)
    b.cx(12, 13)
    b.p(-0.75 * spec.alpha, 13)
    b.cx(12, 13)
    return b
