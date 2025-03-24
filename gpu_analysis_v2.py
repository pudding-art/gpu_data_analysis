import argparse
import json
import logging
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
    return list(filter(filter_func, events))


def get_gpu_trace_events(trace_data):
    allowed_cats = {"gpu_memcpy", "gpu_user_annotation", "kernel", "gpu_memset"}
    return filter_events(trace_data, lambda event: event.get("ph") == "X" and event.get("cat") in allowed_cats)




def get_gpu_stream_num(trace_data):
    events = filter_events(trace_data,
                           lambda event: event.get("name") == "thread_name" and "stream" in event.get("args").get(
                               "name"))
    stream_ids = [event['tid'] for event in events]
    return stream_ids


def get_gpu_trace_events_seperate(trace_data, stream_ids):
    allowed_cats = {"gpu_memcpy", "gpu_user_annotation", "kernel", "gpu_memset"}
    events = filter_events(trace_data, lambda event: event.get("ph") == "X" and event.get("cat") in allowed_cats)
    stream_events = {stream_id: [] for stream_id in stream_ids}

    for event in events:
        event_tid = event.get("tid")
        if event_tid in stream_ids:
            stream_events[event_tid].append(event)
        else:
            logging.info("Event tid {} not in stream_ids".format(event_tid))

    sorted_stream_events = {stream_id: events for stream_id, events in
                            sorted(stream_events.items(), key=lambda item: len(item[1]))}

    return sorted_stream_events


def get_start_time(trace_data):
    filtered_events = filter_events(trace_data, lambda event: event.get("name") == "Iteration Start: PyTorch Profiler")
    return filtered_events[0].get("ts") if filtered_events else None


def get_end_time(trace_data):
    filtered_events = filter_events(trace_data, lambda event: event.get("name") == "Record Window End")
    return filtered_events[0].get("ts") if filtered_events else None


def process_trace_events(trace_events):
    return [(event["ts"], event["ts"] + event["dur"] * 1e3) for event in trace_events if
            "ts" in event and "dur" in event]


def find_intersection(merged_intervals, new_intervals):
    intersection_intervals = []
    cumulative_intersection_time = 0.0

    if not merged_intervals or not new_intervals:
        return intersection_intervals, cumulative_intersection_time

    new_intervals.sort(key=lambda x: x[0])

    for now_interval in merged_intervals:
        start, end = now_interval
        idx = bisect_left(new_intervals, (start,))

        while idx < len(new_intervals) and new_intervals[idx][0] <= end:
            intersection_start = max(start, new_intervals[idx][0])
            intersection_end = min(end, new_intervals[idx][1])
            if intersection_start < intersection_end:
                cumulative_intersection_time += intersection_end - intersection_start
                intersection_intervals.append((intersection_start, intersection_end, cumulative_intersection_time))
            idx += 1

    return intersection_intervals, cumulative_intersection_time


def preprocess_intervals(intervals):
    if not intervals:
        return []

    merged = [intervals[0]]
    preprocessed_intervals = []
    intervals.sort(key=lambda x: x[0])
    file_path = "./test.json"
    with open(file_path, 'w') as f:
        json.dump(intervals, f, indent=4)

    count = 0
    for current in intervals[1:]:
        lasted_merged = merged[-1]
        if current[0] <= lasted_merged[1]:
            merged[-1] = (lasted_merged[0], max(lasted_merged[1], current[1]))
            count += 1
        else:
            preprocessed_intervals.append(lasted_merged)
            merged.append(current)

    preprocessed_intervals.append(merged[-1])

    return preprocessed_intervals


def merge_intervals(intervals_list):
    merged_intervals = []

    for intervals in intervals_list:
        if not merged_intervals:
            merged_intervals = intervals
        else:
            merged_intervals = find_intersection(merged_intervals, intervals)

    return merged_intervals


def merge_intervals_and_find_intersection(intervals_by_stream, start_time, end_time):
    if not intervals_by_stream:
        return [], [(start_time, end_time, 0.0)], end_time - start_time

    for stream_id, intervals in intervals_by_stream.items():
        # intervals.sort(key=lambda x: x[0])
        intervals = preprocess_intervals(intervals)
        intervals_by_stream[stream_id] = intervals

    # logging.info("intervals_by_stream has been sorted.")
    intersection_intervals, cumulative_intersection_time = merge_intervals(list(intervals_by_stream.values()))

    return intersection_intervals, cumulative_intersection_time


def calculate_intersection_time_up_to_tag(intersection_intervals, tag):
    index = bisect_left(intersection_intervals, (tag, float('inf'), float('inf')))
    if index == 0:
        return 0.0
    if index < len(intersection_intervals) and intersection_intervals[index][0] <= tag <= intersection_intervals[index][1]:
        return intersection_intervals[index-1][2] + (tag - intersection_intervals[index][0])
    else:
        return intersection_intervals[index-1][2]


def save_intervals_to_file(intervals, trace_start_time, trace_end_time, base_time_nanoseconds, file_path):
    data = {
        "trace_start_time": trace_start_time,
        "trace_end_time": trace_end_time,
        "base_time_nanoseconds": base_time_nanoseconds,
        "intervals": intervals
    }
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def load_intervals_from_file(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            if not isinstance(data,
                              dict) or "trace_start_time" not in data or "trace_end_time" not in data or "base_time_nanoseconds" not in data or "intervals" not in data:
                logging.error(f"Invalid format in empty intervals file: {file_path}")
                return None, None, None
            intervals = [tuple(interval) for interval in data["intervals"]]
            return data["trace_start_time"], data["trace_end_time"], data["base_time_nanoseconds"], intervals
    except FileNotFoundError:
        logging.info(f"Empty intervals file not found: {file_path}. Will compute from scratch.")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON format in empty intervals file: {file_path}")
    except Exception as e:
        logging.error(f"Error loading empty intervals file: {e}")
    return None, None, None, None


def main(trace_file, user_start_time, user_end_time, time_unit):
    intersection_intervals_file = "./intersection_intervals.json"
    trace_start_time, trace_end_time, base_time_nanoseconds, intersection_intervals = load_intervals_from_file(
        intersection_intervals_file)

    if intersection_intervals is not None:
        logging.info(f"Loaded empty intervals from {intersection_intervals_file}")
        # total_intersection_duration = intersection_intervals[-1][2] + (intersection_intervals[-1][1] - intersection_intervals[-1][0])
        total_intersection_duration = intersection_intervals[-1][2]

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

        stream_ids = get_gpu_stream_num(trace_data)

        gpu_trace_events = get_gpu_trace_events_seperate(trace_data, stream_ids)
        # logging.info(f"gpu_trace_event type is {type(gpu_trace_events)} and len is {len(gpu_trace_events)}")

        intervals_by_stream = {stream_id: process_trace_events(events) for stream_id, events in
                               gpu_trace_events.items()}
        # logging.info(f"intervals_by_stream type is {type(intervals_by_stream)} and len is {len(intervals_by_stream)}")

        intersection_intervals, total_intersection_duration = merge_intervals_and_find_intersection(intervals_by_stream,
                                                                                                    trace_start_time,
                                                                                                    trace_end_time)

        save_intervals_to_file(intersection_intervals, trace_start_time, trace_end_time, base_time_nanoseconds,
                               intersection_intervals_file)

    start_intersection_duration = 0
    end_intersection_duration = total_intersection_duration

    conversion_factor = {
        's': 1e9,
        'ms': 1e6,
        'us': 1e3,
        'ns': 1
    }

    if user_start_time is not None:
        user_start_time_ns = user_start_time * conversion_factor[time_unit]
        if user_start_time_ns - base_time_nanoseconds >= trace_start_time and user_start_time_ns - base_time_nanoseconds <= trace_end_time:
            start_intersection_duration = calculate_intersection_time_up_to_tag(intersection_intervals,
                                                                                user_start_time_ns - base_time_nanoseconds)
        else:
            logging.error("user_start_time is out of range.")
            return

    if user_end_time is not None:
        user_end_time_ns = user_end_time * conversion_factor[time_unit]
        if user_end_time_ns - base_time_nanoseconds >= trace_start_time and user_end_time_ns - base_time_nanoseconds <= trace_end_time:
            end_intersection_duration = calculate_intersection_time_up_to_tag(intersection_intervals,
                                                                              user_end_time_ns - base_time_nanoseconds)
        else:
            logging.error("user_end_time is out of range.")
            return

    total_intersection_duration = end_intersection_duration - start_intersection_duration
    logging.info(f"Total GPU intersection time: {total_intersection_duration} ns")

    gpu_intersection_percentage = total_intersection_duration / (trace_end_time - trace_start_time) * 100
    logging.info(f"GPU stream intersection percentage: {gpu_intersection_percentage:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate GPU idle time (percentage).")
    parser.add_argument("-t", "--trace", type=str, required=True, help="Trace file.")
    parser.add_argument("-s", "--start_time", type=float, help="User-provided start time.")
    parser.add_argument("-e", "--end_time", type=float, help="User-provided end time.")
    parser.add_argument("-u", "--unit", type=str, choices=['s',  'ms', 'us','ns'], default='ns',
                        help="Time unit of user-provided times (default: ns).")
    args = parser.parse_args()
    main(args.trace, args.start_time, args.end_time, args.unit)
