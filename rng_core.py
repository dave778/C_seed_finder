import os, sys, subprocess, importlib
import numpy as np
from concurrent.futures import ProcessPoolExecutor

HAS_EXTENSION = False
try:
    import search_rng_module
    HAS_EXTENSION = True
except ImportError:
    # Try to auto-build
    try:
        print("⚠️ Extension not found, attempting to build...")
        subprocess.check_call([sys.executable, "setup.py", "build_ext", "--inplace"])
        import search_rng_module
        HAS_EXTENSION = True
    except Exception as e:
        print(f"⚠️ Build failed: {e}")
        HAS_EXTENSION = False


def lcg_jump(seed, a, c, m, steps):
    """Jump ahead using matrix exponentiation (Python fallback)."""
    # Use 2x2 matrix [[a, c],[0,1]] ^ steps
    def matmul(X, Y):
        return np.array([
            [(X[0,0]*Y[0,0] + X[0,1]*Y[1,0]) % m,
             (X[0,0]*Y[0,1] + X[0,1]*Y[1,1]) % m],
            [(X[1,0]*Y[0,0] + X[1,1]*Y[1,0]) % m,
             (X[1,0]*Y[0,1] + X[1,1]*Y[1,1]) % m]
        ], dtype=np.uint64)

    def matpow(M, power):
        result = np.array([[1,0],[0,1]], dtype=np.uint64)
        while power > 0:
            if power & 1:
                result = matmul(result, M)
            M = matmul(M, M)
            power >>= 1
        return result

    M = np.array([[a, c],[0,1]], dtype=np.uint64)
    Mp = matpow(M, steps)
    return (Mp[0,0]*seed + Mp[0,1]) % m


def generate_draws(seed, draws, a, c, m):
    """Vectorized RNG draw generation (Python fallback)."""
    rng = np.empty(draws, dtype=np.uint64)
    state = seed
    for i in range(draws):
        state = (a*state + c) % m
        rng[i] = state % 80 + 1
    return rng


def numpy_search_and_predict(seed, jump_count, duration, rate, target20, target10):
    """Pure Python fallback version with vectorization + multiprocessing."""
    a = np.uint64(6364136223846793005)
    c = np.uint64(1442695040888963407)
    m = np.uint64(2**64)

    # Jump ahead
    state = lcg_jump(seed, a, c, m, jump_count)

    total_draws = duration * rate * 20
    arr = generate_draws(state, total_draws, a, c, m)

    matches = []

    # Search for full 20-set (exact or >=75% overlap)
    for i in range(0, len(arr)-20, 20):
        window = np.sort(arr[i:i+20])
        overlap = np.intersect1d(window, target20).size
        if overlap == 20:
            matches.append({"match_type": "full_20", "start_index": i, "confidence_score": 1.0})
        elif overlap >= 15:
            score = overlap / 20.0
            matches.append({"match_type": "partial_20", "start_index": i, "confidence_score": score})

    # Search for 10-subset
    for i in range(0, len(arr)-20, 20):
        window = np.sort(arr[i:i+20])
        overlap = np.intersect1d(window, target10).size
        if overlap == 10:
            matches.append({"match_type": "full_10", "start_index": i, "confidence_score": 1.0})

    return matches


def search_and_predict(seed, jump_count, duration, rate, target20, target10):
    if HAS_EXTENSION:
        return search_rng_module.search_and_predict(
            int(seed), int(jump_count), int(duration), int(rate),
            list(map(int, target20)), list(map(int, target10))
        )
    else:
        return numpy_search_and_predict(seed, jump_count, duration, rate, target20, target10)