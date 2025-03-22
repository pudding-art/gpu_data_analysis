import json
from typing import List, Tuple, Optional
from bisect import bisect_left
import argparse
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def open_file(trace_file):
    try:
        with open(trace_file, 'r') as trace:
            return json.load(trace)
    except FileNotFoundError:
        logging.error(f"File not found: {trace_file}")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format: {trace_file}")
    except Exception as e:
        logging.error(f"Other error: {e}")
    return None

def filter_events(trace_data, filter_func):
    events = trace_data.get("traceEvents", [])
    return list(filter(filter_func, events))

def get_gpu_trace_events(trace_data):
    allowed_cats = {"gpu_memcpy", "gpu_user_annotation", "kernel", "gpu_memset"}
    return filter_events(trace_data, lambda event: event.get("ph") == "X" and event.get("cat") in allowed_cats)

def get_start_time(trace_data):
    filtered_events = filter_events(trace_data, lambda event: event.get("name") == "Iteration Start: PyTorch Profiler")
    return filtered_events[0].get("ts") if filtered_events else None

def get_end_time(trace_data):
    filtered_events = filter_events(trace_data, lambda event: event.get("name") == "Record Window End")
    return filtered_events[0].get("ts") if filtered_events else None

def process_trace_events(trace_events):
    return [(event["ts"], event["ts"] + event["dur"] * 1e3) for event in trace_events if "ts" in event and "dur" in event]

def merge_intervals_and_find_empty(intervals, start_time, end_time):
    if not intervals:
        return [], [(start_time, end_time, 0.0)], end_time - start_time

    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    empty_intervals = []
    cumulative_empty_time = 0.0

    # Check if there is an empty interval before the first merged interval
    if merged[0][0] > start_time:
        empty_intervals.append((start_time, merged[0][0], 0.0))
        cumulative_empty_time += merged[0][0] - start_time

    for current in intervals[1:]:
        last_merged = merged[-1]
        if current[0] <= last_merged[1]:  # Overlapping or touching intervals
            merged[-1] = (last_merged[0], max(last_merged[1], current[1]))
        else:
            # Check if there is an empty interval between the last merged interval and the current interval
            if current[0] > last_merged[1]:
                empty_intervals.append((last_merged[1], current[0], cumulative_empty_time))
                cumulative_empty_time += current[0] - last_merged[1]
            merged.append(current)

    # Check if there is an empty interval after the last merged interval
    if merged[-1][1] < end_time:
        empty_intervals.append((merged[-1][1], end_time, cumulative_empty_time))
        cumulative_empty_time += end_time - merged[-1][1]

    return merged, empty_intervals, cumulative_empty_time


def calculate_empty_time_up_to_tag(empty_intervals, tag):
    index = bisect_left(empty_intervals, (tag, float('inf'), float('inf')))
    if index == 0:
        return 0.0

    if index < len(empty_intervals) and empty_intervals[index][0] <= tag <= empty_intervals[index][1]:
        return empty_intervals[index][2] + (tag - empty_intervals[index][0])
    else:
        return empty_intervals[index][2]

    # return empty_intervals[index-1][2] + (tag - empty_intervals[index-1][0])


def save_empty_intervals_to_file(empty_intervals, trace_start_time, trace_end_time,base_time_nanoseconds, file_path):
    data = {
        "trace_start_time": trace_start_time,
        "trace_end_time": trace_end_time,
        "base_time_nanoseconds": base_time_nanoseconds,
        "empty_intervals": empty_intervals
    }
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def load_empty_intervals_from_file(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict) or "trace_start_time" not in data or "trace_end_time" not in data or "base_time_nanoseconds" not in data or "empty_intervals" not in data:
                logging.error(f"Invalid format in empty intervals file: {file_path}")
                return None, None, None
            empty_intervals = [tuple(interval) for interval in data["empty_intervals"]]
            return data["trace_start_time"], data["trace_end_time"], data["base_time_nanoseconds"], empty_intervals
    except FileNotFoundError:
        logging.info(f"Empty intervals file not found: {file_path}. Will compute from scratch.")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in empty intervals file: {file_path}")
    except Exception as e:
        logging.error(f"Error loading empty intervals file: {e}")
    return None, None, None, None


def main(trace_file, user_start_time, user_end_time, time_unit):

    empty_intervals_file = "./empty_intervals.json"
    trace_start_time, trace_end_time, base_time_nanoseconds, empty_intervals = load_empty_intervals_from_file(empty_intervals_file)

    if empty_intervals is not None:
        logging.info(f"Loaded empty intervals from {empty_intervals_file}")
        total_empty_duration = empty_intervals[-1][2] + (empty_intervals[-1][1] - empty_intervals[-1][0])
    else:
        trace_data = open_file(trace_file)
        if trace_data is None:
            logging.error("Failed to load trace file.")
            return

        base_time_nanoseconds = trace_data.get("baseTimeNanoseconds")
        display_time_unit = trace_data.get("displayTimeUnit")

        trace_start_time = get_start_time(trace_data)
        trace_end_time = get_end_time(trace_data)

        if trace_start_time is None or trace_end_time is None:
            logging.error("Start or end time not found in trace data.")
            return

        gpu_trace_events = get_gpu_trace_events(trace_data)
        intervals = process_trace_events(gpu_trace_events)
        merged_intervals, empty_intervals, total_empty_duration = merge_intervals_and_find_empty(intervals, trace_start_time, trace_end_time)


        save_empty_intervals_to_file(empty_intervals, trace_start_time, trace_end_time, base_time_nanoseconds, empty_intervals_file)


    start_empty_duration = 0
    end_empty_duration = total_empty_duration

    conversion_factor = {
        's': 1e9,
        'ms': 1e6,
        'us': 1e3,
        'ns': 1
    }

    if user_start_time is not None:
        user_start_time_ns = user_start_time * conversion_factor[time_unit]
        if user_start_time_ns - base_time_nanoseconds >= trace_start_time and user_start_time_ns - base_time_nanoseconds <= trace_end_time:
            start_empty_duration = calculate_empty_time_up_to_tag(empty_intervals,
                                                                  user_start_time_ns - base_time_nanoseconds)
        else:
            logging.error("user_start_time is out of range.")
            return

    if user_end_time is not None:
        user_end_time_ns = user_end_time * conversion_factor[time_unit]
        if user_end_time_ns - base_time_nanoseconds >= trace_start_time and user_end_time_ns - base_time_nanoseconds <= trace_end_time:
            end_empty_duration = calculate_empty_time_up_to_tag(empty_intervals,
                                                                  user_end_time_ns - base_time_nanoseconds)
        else:
            logging.error("user_end_time is out of range.")
            return


    total_empty_duration =  end_empty_duration - start_empty_duration
    logging.info(f"Total GPU idle time: {total_empty_duration} ns")

    gpu_idle_percentage = total_empty_duration / (trace_end_time - trace_start_time) * 100
    logging.info(f"GPU idle percentage: {gpu_idle_percentage:.2f}%")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate GPU idle time (percentage).")
    parser.add_argument("-t", "--trace", type=str, required=True, help="Trace file.")
    parser.add_argument("-s", "--start_time", type=float, help="User-provided start time.")
    parser.add_argument("-e", "--end_time", type=float, help="User-provided end time.")
    parser.add_argument("-u", "--unit", type=str, choices=['s', 'ms', 'ns'], default='ns',
                        help="Time unit of user-provided times (default: ns).")
    args = parser.parse_args()
    main(args.trace, args.start_time, args.end_time, args.unit)


