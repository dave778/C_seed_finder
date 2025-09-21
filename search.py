# search.py
import multiprocessing as mp
import time
import uuid
from typing import List, Dict, Any
from storage import save_session
from utils import format_time_offset

def compute_jump_count_from_2001(draws_per_second: int) -> int:
    import datetime
    base = datetime.datetime(2001,1,1,tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    secs = int((now - base).total_seconds())
    return secs * draws_per_second

def _call_task(task):
    func, args = task
    return func(*args)

def run_parallel_search(c_extension_callable, seeds: List[int], jump_count: int, search_duration_seconds: int,
                        draws_per_second: int, target20: List[int], target10: List[int],
                        numbers_per_draw: int = 20, match_threshold: float = 0.75, unbiased: int = 1,
                        a: int = None, c: int = None, processes: int = None) -> List[Dict[str,Any]]:
    tasks = []
    for s in seeds:
        if a is not None and c is not None:
            args = (int(s), int(jump_count), int(search_duration_seconds), int(draws_per_second),
                    target20, target10, int(numbers_per_draw), float(match_threshold), int(unbiased), int(a), int(c))
        else:
            args = (int(s), int(jump_count), int(search_duration_seconds), int(draws_per_second),
                    target20, target10, int(numbers_per_draw), float(match_threshold), int(unbiased))
        tasks.append((c_extension_callable, args))

    procs = processes or mp.cpu_count()
    pool = mp.Pool(processes=procs)
    start = time.time()
    results = pool.map(_call_task, tasks)
    pool.close()
    pool.join()
    elapsed = time.time() - start

    aggregated = []
    for seed, res in zip(seeds, results):
        if isinstance(res, list):
            for item in res:
                mt = item.get("match_type")
                draw_idx = int(item.get("draw_index"))
                conf = float(item.get("confidence_score"))
                seconds_offset = int(round(draw_idx / float(draws_per_second)))
                aggregated.append({
                    "seed": seed,
                    "match_type": mt,
                    "draw_index": draw_idx,
                    "confidence": conf,
                    "time_offset_seconds": seconds_offset,
                    "time_offset_pretty": format_time_offset(seconds_offset)
                })
        else:
            aggregated.append({"seed": seed, "error": str(res)})
    sid = str(uuid.uuid4())
    payload = {"created": time.time(), "seeds": seeds, "results_count": len(aggregated), "elapsed": elapsed}
    save_session(sid, payload)
    return aggregated