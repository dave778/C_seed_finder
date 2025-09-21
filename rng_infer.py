# rng_infer.py - basic LCG inference helper
# Attempt to infer A and C from three consecutive 64-bit outputs x0,x1,x2:
# x1 = A*x0 + C (mod 2^64)
# x2 = A*x1 + C (mod 2^64)
# subtract gives: (x2-x1) = A*(x1-x0) (mod 2^64)
# If (x1-x0) is odd (i.e., invertible mod 2^64), we can compute A and then C.

from typing import Tuple, Optional

def modinv_2pow(a: int) -> Optional[int]:
    # compute modular inverse modulo 2^64 for odd a via Newton-Raphson
    if a % 2 == 0:
        return None
    mod = 1 << 64
    inv = 1
    for _ in range(6):
        inv = (inv * (2 - a * inv)) % mod
    return inv

def infer_lcg_params(x0: int, x1: int, x2: int) -> Optional[Tuple[int,int]]:
    mod = 1 << 64
    d1 = (x1 - x0) % mod
    d2 = (x2 - x1) % mod
    inv = modinv_2pow(d1)
    if inv is None:
        return None
    A = (d2 * inv) % mod
    C = (x1 - (A * x0) % mod) % mod
    return (A, C)