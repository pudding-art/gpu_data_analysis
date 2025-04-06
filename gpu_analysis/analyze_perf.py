import re
import json
import argparse
from collections import defaultdict
from typing import List, Dict, Set,Tuple, Optional

# Regex to parse relevant perf script lines (adjust if your format differs slightly)
# Handles common formats, including potential task names with spaces if needed later
CONFIG = {
    "line_regex": r'^\s*(.+?)\s+(\d+)\s+\[(\d+)\]\s+([\d\.]+):\s+(\S+):\s+(.*)$',
    "sched_switch_regex": r'prev_comm=(.+)\s+prev_pid=(\d+)\s+prev_prio=(\d+)\s+prev_state=(\S+)\s+==>\s+next_comm=(.+)\s+next_pid=(\d+)\s+next_prio=(\d+)',
    "syscall_regex": r'(sys_enter|sys_exit):\s+NR\s+\d+\s+\(.*\)',
    "output_format": "json"
}

class EventParser:
    def __init__(self, config: Dict):
        self.config = config
        self.line_re = re.compile(config["line_regex"])
        self.switch_re = re.compile(config["sched_switch_regex"])
        self.syscall_re = re.compile(config["syscall_regex"])

    def parse_line(self, line: str, line_num) -> Optional[Dict]:
        match = self.line_re.match(line)
        if not match:
            # Handle lines that don't match the format (e.g., headers, comments)
            print(f"Warning: Skipping malformed line {line_num + 1}: {line.strip()}")
            return None
        task_name, pid_str, cpu_str, ts_str, event_name, details = match.groups()
        try:
            pid = int(pid_str)
            cpu = int(cpu_str)
            timestamp = float(ts_str)
        except ValueError:
            print(f"Warning: Skipping line {line_num + 1} due to parsing error: {line.strip()}")
            return None
        return {
            "task_name": task_name,
            "pid": pid,
            "cpu": cpu,
            "timestamp": timestamp,
            "event_name": event_name,
            "details": details
        }

    def parse_sched_switch(self, details: str, line_num) -> Optional[Dict]:
        match = self.switch_re.match(details)
        if not match:
            print(f"Warning: Skipping malformed sched_switch line {line_num + 1}: {details.strip()}")
            return None
        prev_comm, prev_pid_str, _prio, prev_state, next_comm, next_pid_str, _nprio = match.groups()
        try:
            prev_pid = int(prev_pid_str)
            next_pid = int(next_pid_str)
        except ValueError:
            return None
        return {
            "prev_comm": prev_comm,
            "prev_pid": prev_pid,
            "prev_state": prev_state,
            "next_comm": next_comm,
            "next_pid": next_pid
        }

    def parse_syscall(self, details: str, line_num) -> Optional[Dict]:
        match = self.syscall_re.match(details)
        if not match:
            print(f"Warning: Skipping malformed syscall line {line_num + 1}: {details.strip()}")
            return None
        syscall_type, nr, args = match.groups()
        return {
            "syscall_type": syscall_type,
            "nr": nr,
            "args": args
        }


# Mapping from kernel state to our simplified states
def get_state_after_switch(prev_state_str):
    """Determines if the process is ready ('preempt') or non-ready ('sleep') after being switched out."""
    # R = Running or Runnable, R+ = Runnable + Wake Preempt (Linux 5.14+)
    if 'R' in prev_state_str:
        return 'preempt'  # Ready but waiting for CPU
    else:
        # S = Interruptible Sleep, D = Uninterruptible Disk Sleep, T = Stopped, etc.
        return 'sleep'  # Non-ready (waiting for I/O, timer, lock, etc.)


def intersect_intervals(interval1: Tuple[float, float], interval2: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    start = max(interval1[0], interval2[0])
    end = min(interval1[1], interval2[1])
    if start < end:
        return start, end
    return None


def parse_perf_log(log_file, target_pids=None, config = CONFIG):
    """
    Parses the perf log file and generates state intervals.

    Args:
        log_file (str): Path to the perf.log file.
        target_pids (set, optional): A set of PIDs to focus on. If None, analyze all PIDs.

    Returns:
        list: A list of dictionaries, each representing a state interval in the JSON format.
    """
    process_states = {}  # pid -> {'state': str, 'last_timestamp': float, 'cpu': int}
    intervals = []  # Stores raw interval data: (pid, start_ts, end_ts, state)
    syscall_intervals = defaultdict(list)  # pid -> [(start, end)]
    parser = EventParser(config=config)
    min_ts = float('inf')
    max_ts = 0.0

    print(f"Processing log file: {log_file}")
    if target_pids:
        print(f"Focusing on PIDs: {target_pids}")


    with open(log_file, 'r') as f:
        for line_num, line in enumerate(f):
            # match = line_re.match(line)
            event = parser.parse_line(line, line_num)
            if not event:
                # Handle lines that don't match the primary format (e.g., headers, comments)
                if line.strip().startswith('#') or not line.strip():
                    continue
                # print(f"Warning: Skipping malformed line {line_num + 1}: {line.strip()}")
                continue

            pid = event['pid']
            timestamp = event['timestamp']
            event_name = event['event_name']

            # Update overall time range
            min_ts = min(min_ts, timestamp)
            max_ts = max(max_ts, timestamp)

            # --- Core Logic: Process sched_switch ---
            if event_name == 'sched:sched_switch':
                switch_event = parser.parse_sched_switch(event['details'], line_num)
                # switch_match = switch_re.match(details.strip())
                if not switch_event:
                    # print(f"Warning: Skipping malformed sched_switch line {line_num + 1}: {event['details'].strip()}")
                    continue


                prev_pid = switch_event['prev_pid']
                next_pid = switch_event['next_pid']

                # --- Handle Previous Process ---
                # Should we track this process?
                if target_pids is None or prev_pid in target_pids:
                    if prev_pid in process_states:
                        # Process was previously running, record the 'running' interval
                        prev_event = process_states[prev_pid]
                        if prev_event['state'] == 'running':  # Should always be true if tracked correctly
                            start_time = prev_event['last_timestamp']
                            duration = timestamp - start_time
                            if duration > 0:  # Avoid zero-duration intervals
                                intervals.append({
                                    'pid': prev_pid,
                                    'start': start_time,
                                    'end': timestamp,
                                    'state': 'running'
                                })
                        # else: Record unexpected previous state if needed for debugging
                        #    print(f"Debug: prev_pid {prev_pid} was in state {prev_event['state']} before switch at {timestamp}")

                        # Update state to off-cpu (preempt or sleep)
                        new_state = get_state_after_switch(switch_event['prev_state'])
                        process_states[prev_pid] = {
                            'state': new_state,
                            'last_timestamp': timestamp,
                            'cpu': -1}  # No longer on this CPU
                        # else:
                        # This might happen if the process started running before our trace window or on another CPU
                        # We can't determine the start of its running interval accurately here.
                        # For simplicity, we assume tracking starts when it first appears as next_pid
                        # or handle it by setting a default 'unknown' start state if necessary.
                        # To avoid complexity, let's just update its state now based on the switch out.
                        # new_state = get_state_after_switch(prev_state)
                        # process_states[prev_pid] = {'state': new_state, 'last_timestamp': timestamp, 'cpu': -1}
                        # print(f"Info: prev_pid {prev_pid} seen for first time switching out at {timestamp}, state set to {new_state}")
                        pass  # Let's only track state changes robustly after a process has been 'next_pid'

                # --- Handle Next Process ---
                # Should we track this process?
                if target_pids is None or next_pid in target_pids:
                    if next_pid in process_states:
                        # Process was previously off-cpu (preempt or sleep), record that interval
                        prev_event = process_states[next_pid]
                        old_state = prev_event['state']
                        if old_state in ['preempt', 'sleep']:  # Should be one of these
                            start_time = prev_event['last_timestamp']
                            duration = timestamp - start_time
                            if duration > 0:
                                intervals.append({
                                    'pid': next_pid,
                                    'start': start_time,
                                    'end': timestamp,
                                    'state': old_state
                                })
                            # else: # It might have been running on another CPU, which is complex without per-CPU tracking
                            # print(f"Debug: next_pid {next_pid} switched in at {timestamp}, but previous state was {old_state}")
                            pass

                        # Update state to running
                        process_states[next_pid] = {'state': 'running', 'last_timestamp': timestamp, 'cpu': event['cpu']}
                    else:
                        # First time we see this process being scheduled *in*
                        # We assume it was in some off-cpu state before this point, but cannot determine duration/type
                        # Initialize its state as running from now
                        process_states[next_pid] = {'state': 'running', 'last_timestamp': timestamp, 'cpu': event['cpu']}
                        # print(f"Info: next_pid {next_pid} seen for first time switching in at {timestamp}")


            elif event_name == 'raw_syscalls:sys_enter':
                if target_pids is None or pid in target_pids:
                    syscall_intervals[pid].append([timestamp, None])
            elif event_name == 'raw_syscalls:sys_exit':
                if target_pids is None or pid in target_pids:
                    if syscall_intervals[pid] and syscall_intervals[pid][-1][1] is None:
                        syscall_intervals[pid][-1][1] = timestamp

            # --- Handle other event types if needed in the future (e.g., sched_wakeup) ---
            # else:
            #     # For now, ignore other events like syscalls for state determination
            #     pass



    print(f"Finished processing log file. Total time range: {min_ts:.6f}s to {max_ts:.6f}s")

    # --- Finalize Intervals ---
    # At the end of the log, any process still 'running' or 'off-cpu' needs its final interval closed
    print("Finalizing intervals...")
    final_intervals = []
    for pid, data in process_states.items():
        # Filter again in case state was initialized for non-target PIDs briefly
        if target_pids is not None and pid not in target_pids:
            continue

        start_time = data['last_timestamp']
        duration = max_ts - start_time  # End interval at the last timestamp seen in the log
        if duration > 1e-9:  # Use a small epsilon to avoid floating point issues / zero duration
            final_intervals.append({
                'pid': pid,
                'start': start_time,
                'end': max_ts,
                'state': data['state']  # The state it was in when the log ended
            })
    intervals = intervals + final_intervals

    # Calculate sys state intervals by intersecting running intervals with syscall intervals
    sys_intervals = []
    for interval in intervals:
        if interval['state'] == 'running':
            running_start, running_end = interval['start'], interval['end']
            for syscall_start, syscall_end in syscall_intervals[interval['pid']]:
                if syscall_end is None:
                    continue
                intersection = intersect_intervals((running_start, running_end), (syscall_start, syscall_end))
                if intersection:
                    sys_intervals.append({
                        'pid': interval['pid'],
                        'start': intersection[0],
                        'end': intersection[1],
                        'state': 'sys'
                    })

    intervals.extend(sys_intervals)
    intervals.sort(key=lambda x: (x['pid'], x['start']))# Sort for clarity



    # --- Convert to JSON format ---
    json_output = []
    print(f"Converting {len(intervals)} intervals to JSON format...")
    for interval in intervals:
        # start_us = int(interval['start'] * 1_000_000)
        # end_us = int(interval['end'] * 1_000_000)
        start_us = interval['start'] / 1000.0
        end_us = interval['end'] / 1000.0
        duration_us = end_us - start_us

        if duration_us <= 0:  # Skip zero or negative duration intervals
            # print(f"Skipping zero/negative duration interval for PID {interval['pid']}: start={interval['start']:.9f}, end={interval['end']:.9f}")
            continue

        json_output.append({
            "ph": "X",  # Complete event type in Catapult trace format
            "cat": "Trace",  # Category
            "ts": start_us,  # Timestamp in microseconds
            "dur": duration_us,  # Duration in microseconds
            "pid": 'Pids',  # Use the actual Process ID
            "tid": interval['pid'],  # Often PID is used for TID in process-level traces
            "name": interval['state']  # Our calculated state: running, preempt, sleep
        })

    print(f"Generated {len(json_output)} JSON entries.")
    return json_output


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze perf script log for process states (running(usr/sys), preempt, sleep).",
        formatter_class = argparse.RawTextHelpFormatter,
        epilog = """
            Usage Examples:

            # Analyze all processes found in perf.log
            python analyze_perf.py perf.log -o my_analysis.json

            # Analyze only specific PIDs (e.g., 412946 and 413019 from your example)
            python analyze_perf.py perf.log -p 412946,413019 -o specific_pids.json
        """
    )
    parser.add_argument("perf_log_file", help="Path to the perf script output file (perf.log).")
    parser.add_argument("-o", "--output", default="process_states.json", help="Output JSON file name.")
    parser.add_argument("-p", "--pids",
                        help="Comma-separated list of PIDs to analyze (e.g., 1234,5678). Analyzes all if not specified.")

    args = parser.parse_args()

    target_pids = None
    if args.pids:
        try:
            target_pids = set(int(p) for p in args.pids.split(','))
        except ValueError:
            print("Error: Invalid PID list provided. Please use comma-separated integers.")
            exit(1)

    # Parse the log and generate intervals
    trace_events = parse_perf_log(args.perf_log_file, target_pids)

    # Write the JSON output
    try:
        with open(args.output, 'w') as f:
            json.dump(trace_events, f, indent=2)  # Use indent for readability
        print(f"Successfully wrote JSON output to {args.output}")
    except IOError as e:
        print(f"Error writing JSON output to {args.output}: {e}")
        exit(1)
