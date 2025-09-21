// search_rng_module.c
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

// Multiply two 64-bit ints modulo 2^64
static inline uint64_t mul64(uint64_t a, uint64_t b) {
    __uint128_t r = ( __uint128_t ) a * b;
    return (uint64_t) r;
}

// Jump-ahead for LCG using matrix exponentiation of affine transform
static void lcg_jump(uint64_t state, uint64_t A, uint64_t C, uint64_t k, uint64_t *out_state) {
    uint64_t mul = 1;
    uint64_t add = 0;
    uint64_t base_mul = A;
    uint64_t base_add = C;
    uint64_t kk = k;
    while (kk) {
        if (kk & 1ULL) {
            uint64_t new_mul = mul64(mul, base_mul);
            uint64_t t = mul64(base_mul, add);
            uint64_t new_add = t + base_add;
            mul = new_mul;
            add = new_add;
        }
        uint64_t next_base_mul = mul64(base_mul, base_mul);
        uint64_t t2 = mul64(base_mul, base_add);
        uint64_t next_base_add = t2 + base_add;
        base_mul = next_base_mul;
        base_add = next_base_add;
        kk >>= 1;
    }
    *out_state = mul64(mul, state) + add;
}

// Single LCG step
static inline uint64_t lcg_step(uint64_t *state, uint64_t A, uint64_t C) {
    uint64_t s = *state;
    s = mul64(A, s) + C;
    *state = s;
    return s;
}

// Bitmask for numbers 1..80
typedef struct {
    uint64_t lo;
    uint64_t hi;
} bitmask80;

static inline void mask_add(bitmask80 *m, uint8_t v) {
    int idx = (int)v - 1;
    if (idx < 64) m->lo |= (1ULL << idx);
    else m->hi |= (1ULL << (idx - 64));
}

static inline int mask_and_popcount(bitmask80 a, bitmask80 b) {
    uint64_t lo = a.lo & b.lo;
    uint64_t hi = a.hi & b.hi;
    return __builtin_popcountll(lo) + __builtin_popcountll(hi);
}

// Helper: extract & validate sorted list of given length
static int extract_sorted_list(PyObject *listobj, uint8_t *out_arr, Py_ssize_t expected_len) {
    if (!PyList_Check(listobj)) return -1;
    Py_ssize_t n = PyList_Size(listobj);
    if (n != expected_len) return -2;
    long prev = -1;
    for (Py_ssize_t i = 0; i < n; ++i) {
        PyObject *it = PyList_GetItem(listobj, i); // borrowed
        if (!PyLong_Check(it)) return -3;
        long v = PyLong_AsLong(it);
        if (v < 1 || v > 80) return -4;
        if (i > 0 && v <= prev) return -5;
        out_arr[i] = (uint8_t)v;
        prev = v;
    }
    return (int)n;
}

/*
search_and_predict(
    seed: int,
    jump_count: int,
    search_duration_seconds: int,
    draws_per_second: int,
    target_20_list: list[int] (len 20),
    target_10_list: list[int] (len 10),
    numbers_per_draw: int = 20,
    match_threshold: float = 0.75,
    unbiased: int = 1,
    A: int = default,
    C: int = default
)
*/
static PyObject* search_and_predict(PyObject* self, PyObject* args) {
    PyObject *py_seed, *py_jump, *py_search_seconds, *py_draws_per_sec, *py_target20, *py_target10;
    if (!PyArg_ParseTuple(args, "OOOOOO", &py_seed, &py_jump, &py_search_seconds, &py_draws_per_sec, &py_target20, &py_target10)) {
        // try extended parse with optional args by parsing tuple manually below
        PyErr_Clear();
    }
    // manual parse to allow optional trailing args
    Py_ssize_t nargs = PyTuple_Size(args);
    if (nargs < 6) {
        PyErr_SetString(PyExc_TypeError, "Expected at least 6 arguments.");
        return NULL;
    }
    py_seed = PyTuple_GetItem(args, 0);
    py_jump = PyTuple_GetItem(args, 1);
    py_search_seconds = PyTuple_GetItem(args, 2);
    py_draws_per_sec = PyTuple_GetItem(args, 3);
    py_target20 = PyTuple_GetItem(args, 4);
    py_target10 = PyTuple_GetItem(args, 5);

    uint64_t seed = PyLong_AsUnsignedLongLong(py_seed);
    uint64_t jump_count = PyLong_AsUnsignedLongLong(py_jump);
    long search_seconds = PyLong_AsLong(py_search_seconds);
    long draws_per_sec = PyLong_AsLong(py_draws_per_sec);

    int numbers_per_draw = 20;
    double match_threshold = 0.75;
    int unbiased = 1;
    uint64_t A = 6364136223846793005ULL;
    uint64_t C = 1442695040888963407ULL;

    if (nargs >= 7) {
        numbers_per_draw = (int)PyLong_AsLong(PyTuple_GetItem(args,6));
    }
    if (nargs >= 8) {
        match_threshold = PyFloat_AsDouble(PyTuple_GetItem(args,7));
    }
    if (nargs >= 9) {
        unbiased = (int)PyLong_AsLong(PyTuple_GetItem(args,8));
    }
    if (nargs >= 10) {
        A = PyLong_AsUnsignedLongLong(PyTuple_GetItem(args,9));
    }
    if (nargs >= 11) {
        C = PyLong_AsUnsignedLongLong(PyTuple_GetItem(args,10));
    }

    if (search_seconds <= 0 || draws_per_sec <= 0) {
        PyErr_SetString(PyExc_ValueError, "search_duration_seconds and draws_per_second must be > 0");
        return NULL;
    }
    if (numbers_per_draw <= 0 || numbers_per_draw > 80) {
        PyErr_SetString(PyExc_ValueError, "numbers_per_draw must be 1..80");
        return NULL;
    }

    uint8_t target20[20];
    uint8_t target10[10];
    if (extract_sorted_list(py_target20, target20, 20) < 0) {
        PyErr_SetString(PyExc_ValueError, "target_20_list invalid; must be length 20 sorted unique 1..80");
        return NULL;
    }
    if (extract_sorted_list(py_target10, target10, 10) < 0) {
        PyErr_SetString(PyExc_ValueError, "target_10_list invalid; must be length 10 sorted unique 1..80");
        return NULL;
    }

    uint64_t draws = (uint64_t)search_seconds * (uint64_t)draws_per_sec;
    uint64_t total_numbers = draws * (uint64_t)numbers_per_draw;
    if (total_numbers == 0) {
        PyErr_SetString(PyExc_ValueError, "computed total numbers is zero");
        return NULL;
    }
    if (total_numbers > (uint64_t)1200ULL * 1000ULL * 1000ULL) {
        PyErr_SetString(PyExc_MemoryError, "requested generation too large; reduce duration or draws_per_second");
        return NULL;
    }

    uint8_t *numbers = (uint8_t*) malloc((size_t) total_numbers);
    if (!numbers) {
        PyErr_SetString(PyExc_MemoryError, "failed to allocate numbers buffer");
        return NULL;
    }

    bitmask80 mask20 = {0,0}, mask10 = {0,0};
    for (int i=0;i<20;i++) mask_add(&mask20, target20[i]);
    for (int i=0;i<10;i++) mask_add(&mask10, target10[i]);

    typedef struct { int type; uint64_t draw_index; double confidence; } Match;
    size_t cap = 256, cnt = 0;
    Match *matches = (Match*) malloc(cap * sizeof(Match));
    if (!matches) {
        free(numbers);
        PyErr_SetString(PyExc_MemoryError, "failed to allocate matches");
        return NULL;
    }

    uint64_t state = seed;
    lcg_jump(state, A, C, jump_count, &state);

    const uint64_t map_max = 80ULL;
    const uint64_t limit = UINT64_MAX - (UINT64_MAX % map_max);

    Py_BEGIN_ALLOW_THREADS;
    for (uint64_t i=0;i<total_numbers;i++) {
        uint64_t r = lcg_step(&state, A, C);
        if (unbiased) {
            while (r > limit) {
                r = lcg_step(&state, A, C);
            }
        }
        numbers[i] = (uint8_t)((r % 80ULL) + 1ULL);
    }

    for (uint64_t didx=0; didx<draws; ++didx) {
        uint64_t start = didx * (uint64_t)numbers_per_draw;
        bitmask80 dmask = {0,0};
        for (int j=0;j<numbers_per_draw;j++) {
            mask_add(&dmask, numbers[start + j]);
        }
        int inter20 = mask_and_popcount(dmask, mask20);
        double conf20 = (double)inter20 / 20.0;
        if (conf20 >= match_threshold) {
            if (cnt >= cap) {
                size_t nc = cap * 2;
                Match *t = (Match*) realloc(matches, nc * sizeof(Match));
                if (!t) break;
                matches = t;
                cap = nc;
            }
            matches[cnt].type = 0;
            matches[cnt].draw_index = didx;
            matches[cnt].confidence = conf20;
            cnt++;
        }
        int inter10 = mask_and_popcount(dmask, mask10);
        double conf10 = (double)inter10 / 10.0;
        if (conf10 >= match_threshold) {
            if (cnt >= cap) {
                size_t nc = cap * 2;
                Match *t = (Match*) realloc(matches, nc * sizeof(Match));
                if (!t) break;
                matches = t;
                cap = nc;
            }
            matches[cnt].type = 1;
            matches[cnt].draw_index = didx;
            matches[cnt].confidence = conf10;
            cnt++;
        }
    }
    Py_END_ALLOW_THREADS;

    PyObject *py_list = PyList_New(0);
    if (!py_list) {
        free(numbers);
        free(matches);
        PyErr_SetString(PyExc_MemoryError, "failed to allocate result list");
        return NULL;
    }
    for (size_t i=0;i<cnt;i++) {
        PyObject *d = PyDict_New();
        const char *tstr = (matches[i].type == 0) ? "full_20" : "partial_10";
        PyObject *py_type = PyUnicode_FromString(tstr);
        PyObject *py_idx = PyLong_FromUnsignedLongLong(matches[i].draw_index);
        PyObject *py_conf = PyFloat_FromDouble(matches[i].confidence);
        PyDict_SetItemString(d, "match_type", py_type);
        PyDict_SetItemString(d, "draw_index", py_idx);
        PyDict_SetItemString(d, "confidence_score", py_conf);
        Py_DECREF(py_type);
        Py_DECREF(py_idx);
        Py_DECREF(py_conf);
        PyList_Append(py_list, d);
        Py_DECREF(d);
    }

    free(numbers);
    free(matches);
    return py_list;
}

static PyMethodDef SearchMethods[] = {
    {"search_and_predict", search_and_predict, METH_VARARGS, "Jump RNG, generate numbers, and search for targets."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef searchmodule = {
    PyModuleDef_HEAD_INIT,
    "search_rng_module",
    "High-performance RNG search extension",
    -1,
    SearchMethods
};

PyMODINIT_FUNC PyInit_search_rng_module(void) {
    return PyModule_Create(&searchmodule);
}