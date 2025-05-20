# sched_ext调度器实例


首先分析linux内核自带的simple example，而后分析一些已经在企业应用场景实际运行过的案例。

## linux kernel simple example

./tools/sched_ext/

首先要准备好编译工具链并打开相应内核选项，然后生成vmlinux.h,编译调度器。

### scx_simple
一个最小化的sched_ext调度器，用于演示如何基于sched_ext实现基础调度功能，而非生产级解决方案。该调度器分为两种模式：
- 全局加权模式(Global Weighted Vtime):为每个进程维护一个虚拟时间(vtime)，根据权重（weight）计算进程的推进速度
- FIFO模式:按照进程就绪的先后顺序执行，先进入队列的进程优先运行，直到主动放弃CPU或被更高优先级进程抢占。

scx_simple在单socket统一L3缓存系统中表现良好。所有CPU核心共享同一L3缓存，内存访问延迟一致，无需考虑NUMA效应。

simple_select_cpu->scx_bpf_select_cpu_dfl->scx_bpf_dispatch


从cpu角度，如果rq中没有task了，需要先用consume再用dispatch
从task角度，如果选择的cpu是idle状态，也需要通过dispatch来找？

如果idle加入本地队列，那如果不idle，还是在scx_bpf_select_cpu_dfl里体现出来的


```c
__bpf_kfunc s32 scx_bpf_select_cpu_dfl(struct task_struct *p, s32 prev_cpu,
				       u64 wake_flags, bool *is_idle)
{
	if (!ops_cpu_valid(prev_cpu, NULL))
		goto prev_cpu;
    //若内置空闲追踪功能被禁用（用户自定义了ops.update_idle()），则无法使用此默认选择器，返回prev_cpu
	if (!static_branch_likely(&scx_builtin_idle_enabled)) {
		scx_ops_error("built-in idle tracking is disabled");
		goto prev_cpu;
	}

	if (!scx_kf_allowed(SCX_KF_SELECT_CPU)) // 确保当前 BPF 程序被允许调用此内核函数
		goto prev_cpu;

#ifdef CONFIG_SMP
	return scx_select_cpu_dfl(p, prev_cpu, wake_flags, is_idle);
#endif

prev_cpu:
	*is_idle = false;
	return prev_cpu;  // 也没事儿,task的prev_cpu有默认值
}
```

将任务分配到指定队列
scx_bpf_dispatch 的作用是：

- 将任务p加入指定DSQ的FIFO队列中，等待调度执行。
- 支持从不同调度阶段（如 enqueue、select_cpu、dispatch）调用，实现灵活的任务分配策略。
- 可设置任务的运行时间片（slice）和调度标志（enq_flags），控制任务的执行行为。


三种不同调度阶段的行为
1. 从`ops.select_cpu()`或`ops.enqueue()`调用（直接调度）
场景：任务刚被选中或入队，需分配到特定队列。
行为：
存储 @enq_flags 和 @dsq_id，待 select_cpu 返回后执行调度。
若目标为 SCX_DSQ_LOCAL，自动分配到 select_cpu 返回的 CPU 的本地队列。
约束：
不能通过 SCX_DSQ_LOCAL_ON 访问其他 CPU 的本地队列（需先通过 select_cpu 切换到目标 CPU）。
2. 从`ops.dispatch()`调用（批量调度）
场景：需要批量处理多个任务（如突发负载）。
行为：
可调用ops.dispatch_max_batch次，逐个添加任务到调度队列。
通过`scx_bpf_dispatch_nr_slots()`查询剩余可用槽位。
调用`scx_bpf_consume()`刷新批次并重置计数器。
优势：减少调度开销，提升批量任务处理效率。



函数可在 BPF 锁（未来可能引入）下调用，当前无严格锁限制。


2. 时间片与调度触发
有限时间片：任务运行到 slice 耗尽时，自动触发调度切换。
无限时间片：需通过 scx_bpf_kick_cpu() 手动唤醒 CPU，避免任务长期占用资源。

3. 安全调用
允许 “伪调用”（spuriously call）：即使重复调用或参数无效，也不会导致内核错误。
典型场景：调度逻辑中的防御性编程，确保异常流程下的稳定性。

```c
/**
* p:需要调度的目标任务,从enqueue或select_cpu调度时,p必须是当前正在入队的任务,从dispatch调度时没有限制,可以批量调度多个任务
* dsq_id:目标调度队列的ID
* slice:0则保持当前剩余时间片;SCX_SLICE_INF:无限时间片需要手动触发;
* enq_flags:0代表SCX_ENQ_WAKE,唤醒目标CPU(若空闲)
*/
__bpf_kfunc void scx_bpf_dispatch(struct task_struct *p, u64 dsq_id, u64 slice,
				  u64 enq_flags)
{
	if (!scx_dispatch_preamble(p, enq_flags))
		return;

	if (slice)
		p->scx.slice = slice;
	else
		p->scx.slice = p->scx.slice ?: 1;

	scx_dispatch_commit(p, dsq_id, enq_flags);
}
```


simple_enqueue

全局队列调度

```c
void BPF_STRUCT_OPS(simple_enqueue, struct task_struct *p, u64 enq_flags)
{
	stat_inc(1);	/* count global queueing */

	if (fifo_sched) { // fifo调度
		scx_bpf_dispatch(p, SHARED_DSQ, SCX_SLICE_DFL, enq_flags);
	} else { // 优先级调度
		u64 vtime = p->scx.dsq_vtime; // 记录任务已经运行的恶时间

		/*
		 * Limit the amount of budget that an idling task can accumulate
		 * to one slice.
		 */
         // 如果超时还没被调度，则修改被调度的排序时间，防止该任务一直优先级靠前始终占用CPU
		if (vtime_before(vtime, vtime_now - SCX_SLICE_DFL))
			vtime = vtime_now - SCX_SLICE_DFL;

		scx_bpf_dispatch_vtime(p, SHARED_DSQ, SCX_SLICE_DFL, vtime, enq_flags);
	}
}
```


simple_dispatch
直接调用scx_bpf_consume();
```c
void BPF_STRUCT_OPS(simple_dispatch, s32 cpu, struct task_struct *prev)
{
	scx_bpf_consume(SHARED_DSQ);
}
```

simple_running(每次执行的起点)

vtime_before(a, b) 等价于 a < b，检查新任务的虚拟时间是否超过全局时钟

若超过，则将 vtime_now 提升至新任务的虚拟时间，确保全局时钟反映系统中 “运行最久” 的任务状态
```c
void BPF_STRUCT_OPS(simple_running, struct task_struct *p)
{
	if (fifo_sched)
		return;

	/*
	 * Global vtime always progresses forward as tasks start executing. The
	 * test and update can be performed concurrently from multiple CPUs and
	 * thus racy. Any error should be contained and temporary. Let's just
	 * live with it.
	 */
	if (vtime_before(vtime_now, p->scx.dsq_vtime))
		vtime_now = p->scx.dsq_vtime;
}
```

simple_stopping

用于在任务暂停(如阻塞、主动让出CPU)时更新其vtime,倾向于调度vtime小的,weight越大,vtime越小,越优先
```c
void BPF_STRUCT_OPS(simple_stopping, struct task_struct *p, bool runnable)
{
	if (fifo_sched)
		return;

	/*
	 * Scale the execution time by the inverse of the weight and charge.
	 *
	 * Note that the default yield implementation yields by setting
	 * @p->scx.slice to zero and the following would treat the yielding task
	 * as if it has consumed all its slice. If this penalizes yielding tasks
	 * too much, determine the execution time by taking explicit timestamps
	 * instead of depending on @p->scx.slice.
	 */
     // 20ms
	p->scx.dsq_vtime += (SCX_SLICE_DFL - p->scx.slice) * 100 / p->scx.weight;
}
```

simple_enable(每次执行的起点)

在任务首次被纳入调度器管理时初始化其虚拟运行时间（dsq_vtime）。它确保新任务的起始虚拟时间与当前全局时钟同步，避免因初始值异常导致调度不公平：
- fork() → 新任务初始化 → 调用 simple_enable → 任务进入就绪队列
- 任务被唤醒（如 wait_event 完成） → 调用 simple_enable → 任务准备调度
- 任务从非 SCX 调度器切换到 SCX 调度器 → 调用 simple_enable
```c
void BPF_STRUCT_OPS(simple_enable, struct task_struct *p)
{
	p->scx.dsq_vtime = vtime_now;
}
```
simple_enable：确保新任务 “从零开始” 的公平性。

simple_running：确保所有任务 “同步前进” 的公平性


simple_init
```c
s32 BPF_STRUCT_OPS_SLEEPABLE(simple_init)
{
	return scx_bpf_create_dsq(SHARED_DSQ, -1);
}
```

simple_exit
```c
void BPF_STRUCT_OPS(simple_exit, struct scx_exit_info *ei)
{
	UEI_RECORD(uei, ei);
}
```

### scx_qmap

基于加权 FIFO（First-In-First-Out）策略的调度器实现,权重不同按权重，权重相同按照入队时间排序。
```
用户空间            内核空间
  │                   │
  ├─ 创建/唤醒任务 ────► prep_enable() → 分配 per-task 存储
  │                   │
  │                   ├─ enqueue() → 使用 BPF_MAP_TYPE_QUEUE 入队
  │                   │
  │                   ├─ select_cpu() → 基于权重选择 CPU
  │                   │
  │                   ├─ running() → 更新任务执行状态
  │                   │
  │                   └─ dequeue() → 按加权 FIFO 顺序出队
  │
  ▼
```
支持几个新特性


### scx_central


### scx_flatcg
