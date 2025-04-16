//execsnoop.bpf.c
// 包含头文件
#include "vmlinux.h"
#include "execsnoop.h"
#include <bpf/bpf_helpers.h>

static const struct event empty_event = { };

// 定义哈希映射
struct {
	__uint(type, BPF_MAP_TYPE_HASH);
	__uint(max_entries, 10240);
	__type(key, pid_t);
	__type(value, struct event);
} execs SEC(".maps");

// 定义性能事件映射
struct {
	__uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
	__uint(key_size, sizeof(u32));
	__uint(value_size, sizeof(u32));
}events SEC(".maps");

// 定义sys_enter_execve跟踪点函数
SEC("tracepoint/syscalls/sys_enter_execve")
int tracepoint__syscalls__sys_enter_execve(struct trace_event_raw_sys_enter
					   *ctx)
{
	struct event *event;
	const char **args = (const char **)(ctx->args[1]);
	const char *argp;

	// 查询PID
	u64 id = bpf_get_current_pid_tgid();
	pid_t pid = (pid_t) id;

	// 保存一个空的event到哈希映射中
	if (bpf_map_update_elem(&execs, &pid, &empty_event, BPF_NOEXIST)) {
		return 0;
	}
	event = bpf_map_lookup_elem(&execs, &pid);
	if (!event) {
		return 0;
	}
	// 初始化event变量
	event->pid = pid;
	event->args_count = 0;
	event->args_size = 0;

	// 查询第一个参数
	unsigned int ret = bpf_probe_read_user_str(event->args, ARGSIZE,
						   (const char *)ctx->args[0]);
	if (ret <= ARGSIZE) {
		event->args_size += ret;
	} else {
		/* write an empty string */
		event->args[0] = '\0';
		event->args_size++;
	}

	// 查询其他参数，使用pragma unroll控制循环次数
	event->args_count++;
#pragma unroll
	for (int i = 1; i < TOTAL_MAX_ARGS; i++) {
		bpf_probe_read_user(&argp, sizeof(argp), &args[i]);
		if (!argp)
			return 0;

		if (event->args_size > LAST_ARG)
			return 0;

		ret =
		    bpf_probe_read_user_str(&event->args[event->args_size],
					    ARGSIZE, argp);
		if (ret > ARGSIZE)
			return 0;

		event->args_count++;
		event->args_size += ret;
	}

	// 再尝试一次，确认是否还有未读取的参数
	bpf_probe_read_user(&argp, sizeof(argp), &args[TOTAL_MAX_ARGS]);
	if (!argp)
		return 0;

	// 如果还有未读取参数，则增加参数数量（用于输出"..."）
	event->args_count++;

	return 0;
}

// 定义sys_exit_execve跟踪点函数
SEC("tracepoint/syscalls/sys_exit_execve")
int tracepoint__syscalls__sys_exit_execve(struct trace_event_raw_sys_exit *ctx)
{
	u64 id;
	pid_t pid;
	int ret;
	struct event *event;

	// 从哈希映射中查询进程基本信息
	id = bpf_get_current_pid_tgid();
	pid = (pid_t) id;
	event = bpf_map_lookup_elem(&execs, &pid);
	if (!event)
		return 0;

	// 更新返回值和进程名称
	ret = ctx->ret;
	event->retval = ret;
	bpf_get_current_comm(&event->comm, sizeof(event->comm));

	// 提交性能事件
	size_t len = EVENT_SIZE(event);
	if (len <= sizeof(*event))
		bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, event,
				      len);

	// 清理哈希映射
	bpf_map_delete_elem(&execs, &pid);
	return 0;
}
// 定义许可证（前述的BCC默认使用GPL）
char LICENSE[] SEC("license") = "GPL";

