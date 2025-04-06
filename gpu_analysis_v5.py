import argparse
import json
import logging
import os
from bisect import bisect_left

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
    if filter_func is None:
        return events
    return list(filter(filter_func, events))


def get_gpu_trace_events(trace_data):
    allowed_cats = {"gpu_memcpy", "gpu_user_annotation", "kernel", "gpu_memset"}
    return filter_events(trace_data, lambda event: event.get("ph") == "X" and event.get("cat") in allowed_cats)


def get_range(trace_data):
    events = filter_events(trace_data, lambda event: event.get("ts") is not None)
    # if not events:
    #     return None, None
    events = process_trace_events(events)
    # if not events:
    #     return None, None
    events.sort(key=lambda x: x[0])
    return events[0][0], events[-1][1]


def get_start_time(trace_data):
    filtered_events = filter_events(trace_data, lambda event: event.get("name") == "Iteration Start: PyTorch Profiler")
    return filtered_events[0].get("ts") * 1e3 if filtered_events else None


def get_end_time(trace_data):
    filtered_events = filter_events(trace_data, lambda event: event.get("name") == "Record Window End")
    return filtered_events[0].get("ts") * 1e3 if filtered_events else None


def process_trace_events(trace_events):
    return [(event["ts"] * 1e3, event["ts"] * 1e3 + event["dur"] * 1e3) for event in trace_events if
            "ts" in event and "dur" in event]


def filter_events_beyond_threshold(gpu_trace_events, threshold):
    if gpu_trace_events is None:
        return None
    # gpu_trace_events = get_gpu_trace_events(trace_data)
    # gpu_trace_events = process_trace_events(gpu_trace_events)
    gpu_trace_events_beyond_threshold = []
    for event in gpu_trace_events:
        if event[1] - event[0] > threshold:
            gpu_trace_events_beyond_threshold.append(event)

    return gpu_trace_events_beyond_threshold


def filter_trace_events_by_usertime(trace_data, user_start_time, user_end_time):
    if trace_data is None:
        return None

    if user_start_time >= user_end_time:
        logging.error("user_start_time is bigger than user_end_time!")
        return None

    base_time_nanoseconds = trace_data.get("baseTimeNanoseconds")
    user_start_time = user_start_time - base_time_nanoseconds
    user_end_time = user_end_time - base_time_nanoseconds

    # allowed_cats = {"gpu_memcpy", "gpu_user_annotation", "kernel", "gpu_memset"}
    # cpu_events = filter_events(trace_data,
    #                            lambda event: event.get("ph") == "X" and event.get("cat") not in allowed_cats)
    events = filter_events(trace_data, filter_func=None)

    filtered_events = []

    for event in events:
        event_start = event['ts'] * 1e3
        event_end = event_start + event.get('dur', 0) * 1e3
        # print(event_start, event_end)
        if event_start >= user_start_time and event_end <= user_end_time:
            filtered_events.append(event)
        elif event_start < user_start_time and event_end > user_end_time:
            filtered_event = event.copy()
            filtered_event['ts'] = user_start_time
            filtered_event['dur'] = user_end_time
            filtered_events.append(filtered_event)
        elif event_start < user_start_time and event_end > user_start_time:
            filtered_event = event.copy()
            filtered_event['ts'] = user_start_time
            filtered_event['dur'] = event_end - user_start_time
            filtered_events.append(filtered_event)
        elif event_start < user_end_time and event_end > user_end_time:
            filtered_event = event.copy()
            filtered_event['dur'] = user_end_time - event_start
            filtered_events.append(filtered_event)

    return filtered_events


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
            empty_intervals.append((last_merged[1], current[0], cumulative_empty_time))
            cumulative_empty_time += current[0] - last_merged[1]
            merged.append(current)

    # Check if there is an empty interval after the last merged interval
    if merged[-1][1] < end_time:
        empty_intervals.append((merged[-1][1], end_time, cumulative_empty_time))
        cumulative_empty_time += end_time - merged[-1][1]

    return merged, empty_intervals, cumulative_empty_time


def find_index(empty_intervals, tag):
    if empty_intervals is None:
        logging.error("empty_intervals is None.")
        return None

    index = bisect_left(empty_intervals, (tag, float('inf'), float('inf')))
    return index


def calculate_empty_time_up_to_tag(empty_intervals, tag):
    index = find_index(empty_intervals, tag)
    if index == 0:
        return 0.0

    prev_start, prev_end, prev_empty_time = empty_intervals[index - 1]

    if tag < prev_end:
        return index, prev_empty_time + (tag - prev_start)
    else:
        if index < len(empty_intervals):
            return index, empty_intervals[index][2]
        else:
            return index, prev_empty_time + (prev_end - prev_start)


def save_empty_intervals_to_file(empty_intervals, trace_start_time, trace_end_time, base_time_nanoseconds, file_path):
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
            if not isinstance(data,
                              dict) or "trace_start_time" not in data or "trace_end_time" not in data or "base_time_nanoseconds" not in data or "empty_intervals" not in data:
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


def topk_empty_intervals(empty_intervals, topk, base_time_nanoseconds, user_start_time_ns, user_end_time_ns,
                         empty_intervals_start_index, empty_intervals_end_index, trace_file):
    if empty_intervals is None:
        return None

    processed_empty_intervals = []

    prev_start, prev_end, prev_empty_time = empty_intervals[empty_intervals_start_index - 1]
    if user_start_time_ns < prev_end:
        processed_empty_intervals.append(
            (user_start_time_ns, prev_end, prev_empty_time + user_start_time_ns - prev_start))

    prev_start, prev_end, prev_empty_time = empty_intervals[empty_intervals_end_index - 1]
    if user_end_time_ns < prev_end:
        processed_empty_intervals.append((prev_start, user_end_time_ns, prev_empty_time))
    else:
        processed_empty_intervals.append(empty_intervals[empty_intervals_end_index - 1])

    for interval in empty_intervals[empty_intervals_start_index: empty_intervals_end_index - 1]:
        processed_empty_intervals.append(interval)

    processed_empty_intervals.sort(key=lambda x: x[1] - x[0], reverse=True)
    # print(processed_empty_intervals)

    topk = min(topk, len(processed_empty_intervals))

    logging.info(f"Output top{topk} empty intervals during user-defined time span.")

    for i in range(topk):
        start = processed_empty_intervals[i][0] + base_time_nanoseconds
        end = processed_empty_intervals[i][1] + base_time_nanoseconds
        diff = processed_empty_intervals[i][1] - processed_empty_intervals[i][0]
        logging.info(
            f"Num.{i + 1} empty interval(ns):[{start},{end}], difference: {diff}")

        # output filtered events in this interval


def delete_json_file(file):
    try:
        # Check if the file exists
        if os.path.exists(file):
            # Delete the file
            os.remove(file)
            logging.info(f"The file {file} has been successfully deleted.")
        else:
            logging.info(f"The file {file} does not exist and cannot be deleted.")
    except Exception as e:
        logging.info(f"An error occurred while deleting the file: {e}")


def save_json_file(file, data):
    try:
        # Open the file in write mode
        with open(file, 'w', encoding='utf-8') as f:
            # Serialize the data to JSON and write it to the file
            json.dump(data, f, ensure_ascii=False, indent=4)
        logging.info(f"Data has been successfully saved to {file}.")
    except Exception as e:
        logging.error(f"An error occurred while saving the file: {e}")


def filter_cpu_events(trace_file, user_start_time, user_end_time):
    trace_data = open_file(trace_file)
    if trace_data is None:
        logging.error("Failed to load trace file.")
    filtered_trace_data = filter_trace_events_by_usertime(trace_data, user_start_time, user_end_time)
    # print(filtered_trace_data)
    cpu_events = process_trace_events(filtered_trace_data)
    indexed_cpu_events = [(event, index) for index, event in enumerate(cpu_events)]
    indexed_cpu_events.sort(key=lambda x: x[0][1] - x[0][0], reverse=True)
    sorted_indices = [index for _, index in indexed_cpu_events]

    topk = 10
    topk = min(topk, len(cpu_events))

    for i in range(topk):
        original_index = sorted_indices[i]
        logging.info(
            f"Num.{i + 1} cpu event: {filtered_trace_data[original_index]['name']}, duration: {filtered_trace_data[original_index]['dur'] * 1e3} ns")

    # trace_data['traceEvents'] = filtered_trace_data
    # filtered_json_file = "./filtered_trace.json"
    # save_json_file(filtered_json_file, trace_data)


def filter_events_and_save_json(trace_file, user_start_time, user_end_time, filtered_json_file):
    trace_data = open_file(trace_file)
    if trace_data is None:
        logging.error("Failed to load trace file.")

    filter_trace_data = filter_trace_events_by_usertime(trace_data, user_start_time, user_end_time)

    trace_data['traceEvents'] = filter_trace_data
    # filtered_json_file = "./filtered_trace.json"s
    save_json_file(filtered_json_file, trace_data)


def main(trace_file, user_start_time, user_end_time, time_unit, topk, threshold, clean):
    empty_intervals_file = "./empty_intervals.json"

    if clean:
        delete_json_file(empty_intervals_file)

    trace_start_time, trace_end_time, base_time_nanoseconds, empty_intervals = load_empty_intervals_from_file(
        empty_intervals_file)

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

        # trace_start_time = get_start_time(trace_data)
        # trace_end_time = get_end_time(trace_data)
        trace_start_time, trace_end_time = get_range(trace_data)

        if trace_start_time is None or trace_end_time is None:
            logging.error("Start or end time not found in trace data.")
            return

        gpu_trace_events = get_gpu_trace_events(trace_data)
        intervals = process_trace_events(gpu_trace_events)

        logging.info(f"intervals length:{len(intervals)}")
        # filter data with threshold
        if threshold:
            intervals = filter_events_beyond_threshold(intervals, threshold)
        logging.info(f"intervals length beyond threshold:{len(intervals)}")

        merged_intervals, empty_intervals, total_empty_duration = merge_intervals_and_find_empty(intervals,
                                                                                                 trace_start_time,
                                                                                                 trace_end_time)

        save_empty_intervals_to_file(empty_intervals, trace_start_time, trace_end_time, base_time_nanoseconds,
                                     empty_intervals_file)

    start_empty_duration = 0
    user_start_time_ns = trace_start_time
    user_end_time_ns = trace_end_time
    end_empty_duration = total_empty_duration
    empty_intervals_start_index = 0
    empty_intervals_end_index = len(empty_intervals)

    conversion_factor = {
        's': 1e9,
        'ms': 1e6,
        'us': 1e3,
        'ns': 1
    }

    if user_start_time is not None:
        user_start_time_ns = user_start_time * conversion_factor[time_unit]
        if user_start_time_ns - base_time_nanoseconds >= trace_start_time and user_start_time_ns - base_time_nanoseconds <= trace_end_time:
            empty_intervals_start_index, start_empty_duration = calculate_empty_time_up_to_tag(empty_intervals,
                                                                                               user_start_time_ns - base_time_nanoseconds)
        else:
            logging.error("user_start_time is out of range.")
            return

    if user_end_time is not None:
        user_end_time_ns = user_end_time * conversion_factor[time_unit]
        if user_end_time_ns - base_time_nanoseconds >= trace_start_time and user_end_time_ns - base_time_nanoseconds <= trace_end_time:
            empty_intervals_end_index, end_empty_duration = calculate_empty_time_up_to_tag(empty_intervals,
                                                                                           user_end_time_ns - base_time_nanoseconds)
        else:
            logging.error("user_end_time is out of range.")
            return

    total_empty_duration = end_empty_duration - start_empty_duration
    if (total_empty_duration <= 0):
        logging.error("user_end_time is lower than user_start_time")

    logging.info(f"Total GPU idle time: {total_empty_duration} ns")
    logging.info(f"Total GPU time: {trace_end_time - trace_start_time}")
    logging.info(f"Total user-provided time: {user_end_time_ns - user_start_time_ns} ns")

    gpu_idle_percentage0 = total_empty_duration / (trace_end_time - trace_start_time) * 100
    logging.info(f"Overall GPU idle percentage: {gpu_idle_percentage0:.2f}%")

    gpu_idle_percentage1 = total_empty_duration / (user_end_time_ns - user_start_time_ns) * 100
    logging.info(f"User-defined GPU idle percentage: {gpu_idle_percentage1:.2f}%")

    topk_empty_intervals(empty_intervals, topk, base_time_nanoseconds, user_start_time_ns, user_end_time_ns,
                         empty_intervals_start_index, empty_intervals_end_index, trace_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GPU Idle Time Analyzer - Calculate GPU idle percentage and identify top idle intervals",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
        Usage Examples:
    
        Basic Usage:
          # Analyze full trace file and show top 10 idle intervals defaultly
          python3 gpu_analysis_v5.py -t ./trace.json 
    
        Time Range Analysis:
          # Analyze 1ms to 5ms period (default unit: ns)
          python3 gpu_analysis_v5.py -t trace.json -s 1000000 -e 5000000
    
          # Analyze 1.5ms to 3.2ms using millisecond unit, show top 5 intervals
          python gpu_analysis_v5.py -t trace.json -s 1.5 -e 3.2 -u ms -k 5
    
        Advanced Filtering:
          # Filter GPU events shorter than 100us and clean cache
          python3 gpu_analysis_v5.py -t trace.json -d 100000 -c
    
        Full Parameter Example:
          # Analyze 2s-4s range with 1ms threshold, output top 3 intervals, generate filtered trace between start_time(s) and end_time(e) in json format
          python3 gpu_analysis_v5.py \\
              -t /mnt/profiles/trace.json \\
              -s 2 -e 4 -u s \\
              -d 1000000 \\
              -k 3 \\
              -f ./filtered_trace.json
    """)
    parser.add_argument("-t", "--trace", type=str, required=True,
                        help="Path to the input profiling trace file (JSON format)")
    parser.add_argument("-s", "--start_time", type=float,
                        help="Start time for analysis (requires -e)")
    parser.add_argument("-e", "--end_time", type=float,
                        help="End time for analysis (requires -s)")
    parser.add_argument("-u", "--unit", type=str, choices=['s', 'ms', 'us', 'ns'], default='ns',
                        help="Time unit for specified range (s/ms/us/ns), default: ns")
    parser.add_argument("-k", "--topk", type=int, default=10,
                        help="Number of top idle intervals to display, default: 10")
    parser.add_argument("-d", "--threshold", type=float, default=0.0,
                        help="Filter threshold for GPU events (nanoseconds), default: 0")
    parser.add_argument("-c", "--clean", action='store_true',
                        help="Clean cached analysis results (force recalculation)")
    parser.add_argument("-f", "--filtered_json_file", type=str,
                        help="Output path for filtered trace file containing CPU/GPU events")

    args = parser.parse_args()
    main(args.trace, args.start_time, args.end_time, args.unit, args.topk, args.threshold, args.clean)
    filter_events_and_save_json(trace_file=args.trace, user_start_time=args.start_time, user_end_time=args.end_time,
                                filtered_json_file=args.filtered_json_file)

    # filter_cpu_events(args.trace, args.start_time, args.end_time)
    # perfetto(args.trace, args.start_time, args.end_time)
