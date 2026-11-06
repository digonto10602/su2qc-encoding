"""SUMMARY: the reference circuit of the twelve encoding (UE) expressed through the Builder; every angle is a linear function of spec.alpha / spec.beta.

"""
FAMILY = 'seed'
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    b = Builder(spec)
    b.p(-0.75 * spec.alpha, 2)
    b.p(-0.75 * spec.alpha, 5)
    b.p(-0.75 * spec.alpha, 8)
    b.p(-0.75 * spec.alpha, 11)
    return b
