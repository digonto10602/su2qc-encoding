"""SUMMARY: the reference circuit after the deterministic polish passes.

"""
FAMILY = 'seed'
PARENT = None

from su2plaq.compress.builder import Builder


def build(spec):
    b = Builder(spec)
    b.cx(2, 0)
    b.h(2)
    b.rz(-0.25 * spec.alpha, 2)
    b.cx(2, 0)
    b.rz(-0.25 * spec.alpha, 0)
    b.cx(2, 0)
    b.rz(-0.25 * spec.alpha, 0)
    b.cx(3, 1)
    b.cx(2, 1)
    b.rz(-0.25 * spec.alpha, 1)
    b.cx(2, 1)
    b.cx(3, 1)
    b.cx(3, 0)
    b.cx(2, 0)
    b.cx(1, 0)
    b.rz(-0.25 * spec.alpha, 0)
    b.cx(1, 0)
    b.cx(2, 0)
    b.cx(1, 0)
    b.rz(-0.25 * spec.alpha, 0)
    b.cx(1, 0)
    b.cx(3, 0)
    b.cx(3, 1)
    b.h(3)
    b.rz(-2.0 * spec.beta, 3)
    b.cx(3, 1)
    b.cx(2, 1)
    b.rz(-2.0 * spec.beta, 1)
    b.cx(2, 1)
    b.cx(3, 1)
    b.cx(3, 0)
    b.cx(2, 0)
    b.cx(1, 0)
    b.rz(-2.0 * spec.beta, 0)
    b.cx(1, 0)
    b.cx(2, 0)
    b.cx(1, 0)
    b.rz(-2.0 * spec.beta, 0)
    b.cx(1, 0)
    b.cx(3, 0)
    b.h(2)
    b.h(3)
    b.cx(2, 0)
    b.cx(3, 1)
    return b
