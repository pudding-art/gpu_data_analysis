#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <bpf/libbpf.h>
#include <time.h>
#include "execsnoop.h"
#include "execsnoop.skel.h"
 
// libbpf错误和调试信息回调的处理程序。
static int libbpf_print_fn(enum libbpf_print_level level, const char *format,
			   va_list args)
{
#ifdef DEBUGBPF
	return vfprintf(stderr, format, args);
#else
	return 0;
#endif
}
 
// 丢失事件的处理程序。
void handle_lost_events(void *ctx, int cpu, __u64 lost_cnt)
{
	fprintf(stderr, "Lost %llu events on CPU #%d!\n", lost_cnt, cpu);
}
 
// 打印参数（替换'\0'为空格）
static void print_args(const struct event *e)
{
	int args_counter = 0;
 
	for (int i = 0; i < e->args_size && args_counter < e->args_count; i++) {
		char c = e->args[i];
		if (c == '\0') {
			args_counter++;
			putchar(' ');
		} else {
			putchar(c);
		}
	}
	if (e->args_count > TOTAL_MAX_ARGS) {
		fputs(" ...", stdout);
	}
}
 
// 性能事件回调函数(向终端中打印进程名、PID、返回值以及参数)
void handle_event(void *ctx, int cpu, void *data, __u32 data_sz)
{
	const struct event *e = data;
	printf("%-16s %-6d %3d ", e->comm, e->pid, e->retval);
	print_args(e);
	putchar('\n');
}
 
// Bump RLIMIT_MEMLOCK，允许BPF子系统做任何它需要做的事情。  
static void bump_memlock_rlimit(void)
{
	struct rlimit rlim_new = {
		.rlim_cur = RLIM_INFINITY,
		.rlim_max = RLIM_INFINITY,
	};
 
	if (setrlimit(RLIMIT_MEMLOCK, &rlim_new)) {
		fprintf(stderr, "Failed to increase RLIMIT_MEMLOCK limit!\n");
		exit(1);
	}
}
 
int main(int argc, char **argv)
{
	struct execsnoop_bpf *skel;
	struct perf_buffer *pb = NULL;
	int err;
 
	// 1. 设置调试输出函数，libbpf发生错误会回调libbpf_print_fn
	libbpf_set_print(libbpf_print_fn);
 
	// 2. 增大进程限制的内存，默认值通常太小，不足以存入BPF映射的内容
	bump_memlock_rlimit();
 
	// 3. 打开BPF程序
	skel = execsnoop_bpf__open();
	if (!skel) {
		fprintf(stderr, "Failed to open BPF skeleton\n");
		return 1;
	}
 
	// 4. 加载BPF字节码
	err = execsnoop_bpf__load(skel);
	if (err) {
		fprintf(stderr, "Failed to load and verify BPF skeleton\n");
		goto cleanup;
	}
 
	// 5. 挂载BPF字节码到跟踪点
	err = execsnoop_bpf__attach(skel);
	if (err) {
		fprintf(stderr, "Failed to attach BPF skeleton\n");
		goto cleanup;
	}
 
	// 6. 创建 perf buffer 并配置回调函数
	pb = perf_buffer__new(bpf_map__fd(skel->maps.events), 64, handle_event, handle_lost_events, NULL, NULL);
	err = libbpf_get_error(pb);
	if (err) {
		pb = NULL;
		fprintf(stderr, "failed to open perf buffer: %d\n", err);
		goto cleanup;
	}
 
	printf("%-16s %-6s %3s %s\n", "COMM", "PID", "RET", "ARGS");
 
	// 7. 从缓冲区中循环读取数据
	while ((err = perf_buffer__poll(pb, 100)) >= 0) ;
	printf("Error polling perf buffer: %d\n", err);
 
cleanup:
	perf_buffer__free(pb);
	execsnoop_bpf__destroy(skel);
	return err != 0;
}
