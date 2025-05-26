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
支持几个新特性:
- 睡眠安全的每任务存储（ops.prep_enable）,在任务被调度器启用前，为其分配专用存储,睡眠用于可能阻塞的场景
- BPF_MAP_TYPE_QUEUE映射类型
- core-sched，允许BPF程序深入内核调度决策
    - 通过`ops.select_cpu()`选择目标 CPU。
    - 通过`ops.enqueue()`和`ops.dequeue()`控制任务队列。
    - 通过`ops.running()`和`ops.stopping()`管理任务执行状态。

qmap_init->bpf_timer_init->bpf_timer_set_callback->monitor_timerfn->dispatch_highpri(true)/monitor_cpuperf/dump_shared_dsq->
一个shared_dsq,一个highpri_dsq
同时初始化了一个timer,从系统启动阶段就开始收集性能数据，以便发现异常。如果不在初始化时启动定时器，可能导致系统运行初期缺乏监控，无法及时响应负载变换。


qmap_tick的触发时机，当任务时间片耗尽或调度周期到达时会使用这个函数
time slice expired
周期性调度检查
上下文切换




### scx_central

集中式调度器
单 CPU 决策：所有调度决策由一个专用 CPU（调度器 CPU）负责，其他 CPU 无需参与调度逻辑。
无限时间片：工作 CPU 运行任务时使用无限时间片（infinite slices），无需时钟中断（timer ticks）触发调度。
减少开销：避免每个 CPU 独立调度带来的同步和上下文切换成本。

```c
调度器 CPU                     工作 CPU
  │                              │
  ├─ 接收任务调度请求 ───────────►│
  │                              │
  ├─ 做出调度决策 ──────────────►│
  │                              │
  └─ 分配任务到目标 CPU ─────────►│ 执行任务（无限时间片，无时钟中断）

//传统调度
时钟中断 → 调度器抢占任务 → 触发 vmexit → 宿主机处理中断 → 重新进入 VM
//集中式调度
调度器 CPU 提前规划任务 → 工作 CPU 无限执行 → 减少 vmexit 触发
```

适用场景：
虚拟机（VM）运行：减少 vmexit 次数（时钟中断会触发昂贵的 VM 退出）。
高性能计算（HPC）：减少调度干扰，提升计算密集型任务效率。
实时系统：保证关键任务的执行时间确定性。




### scx_flatcg
扁平化cgroup层次调度器
 传统 cgroup 调度的问题
层次化权重计算复杂：传统 cgroup 调度需遍历整个层级树计算每个组的 CPU 份额。
高开销：多级 cgroup 嵌套时，调度决策需递归访问父组，性能下降。

扁平化设计思路
层级合并：将多级 cgroup 结构 “扁平化” 为单层，通过复合权重（compounded weight）直接计算最终份额。
公式：子 cgroup 的有效权重 = 自身权重 × 父组权重 × ... × 根组权重。
```
Root(权重 100) ──┬── GroupA(权重 50) ── Task1
                └── GroupB(权重 200) ──┬── SubGroupB1(权重 100) ── Task2
                                     └── SubGroupB2(权重 200) ── Task3
Task1: 100 × 50 = 5000
Task2: 100 × 200 × 100 = 2,000,000
Task3: 100 × 200 × 200 = 4,000,000
```

O (1) 复杂度：无需遍历层级树，直接通过复合权重计算份额。
缓存友好：单层结构减少内存访问，提升 CPU 缓存命中率。
实验数据：在统一 L3 缓存的单套接字系统中，调度延迟降低 30%+

多层级 cgroup 环境：如云平台容器调度，减少层级嵌套带来的开销。
单节点高性能系统：在共享缓存的多核系统中表现优异。
权重稳定的工作负载：适合长期运行且权重配置较少变化的场景

## production example
### scx_layered

https://github.com/sched-ext/sched_ext/blob/case-studies/scx_layered.md

基于对Meta计算集群中大规模工作负载的性能分析，尽管CPU利用率仅在40%左右波动，但系统性能受限于请求响应延迟的99%分位数（99th percentile latency）。
表面看 CPU 资源大量闲置（60% 未使用），但实际可能因调度策略不合理，导致关键任务无法及时获取 CPU，或被其他杂务抢占资源，最终受限于延迟而非计算能力。
围绕CPU调度策略优化，文中提到四个问题：
- work conservation:是否存在 “有任务待处理，但CPU却处于空闲” 的情况？可能因为任务调度队列设计不合理，导致CPU空转时仍有任务积压在其他队列；或者CPU核心与任务队列的亲和性（Affinity）设置不当，任务无法快速分配到空闲核心
- idle CPU selection:当任务唤醒并寻找 CPU 运行时，如何选择最优空闲核心？
- soft-affinity:系统中除主工作负载外，还运行着维护、监控等杂务（Miscellaneous Workloads）。将杂务限定在部分CPU核心（如专用维护核心），避免与主工作负载竞争资源。
- Custom policies for different threads:主工作负载已为重要线程设置了nice值（Linux进程优先级，值越低优先级越高)

#### work conservation
单Socket內的CPU核心共享缓存L3 cache和内存控制器，通信延迟低，适合采用共享调度队列策略。任意CPU核心空闲时，直接从共享队列中选取就绪线程执行，无需跨队列迁移任务。
原生 CFS/EEVDF：采用 per-CPU 运行队列（每个核心维护独立队列），任务调度需考虑负载均衡（如周期性扫描其他核心队列是否过载），可能存在队列间负载不均导致部分核心空闲。

- David Vernet的共享运行队列补丁：
基于早期sched_ext实验，为原生调度器引入跨核心共享运行队列机制。
效果：生产环境部署后吞吐量提升约1%，证明共享队列在减少核心空闲、提升资源利用率方面的有效性。
- scx_simple调度器：sched_ext 实现的简单示例调度器，仅使用共享队列而未优化空闲 CPU 选择逻辑。
性能与上述共享队列补丁接近，说明**工作守恒本身（而非复杂调度策略）是性能提升的主要原因**。

对于许多工作负载，缓存局部性的收益可能被高估，因此调度策略应优先考虑工作守恒（快速利用空闲 CPU）而非等待原有核心释放。工作守恒优先于缓存局部性的调度策略

超线程（Hyper-Threading）场景的调度选择
超线程 sibling 核心：同一物理核心的两个逻辑核心（如 Intel 的 HT）共享 L1/L2 缓存（但 L1 指令缓存可能独立）。
传统观点：调度任务到原核心的超线程 sibling（逻辑核心 2）可能保留部分缓存数据（因物理核心未执行其他任务）。
新结论：若 L2 缓存局部性不重要（如数据已被逐出），超线程 sibling 与完全空闲的其他物理核心无本质区别，两者均需冷启动缓存。因此无需优先选择超线程 sibling，应直接选择任意空闲核心以实现工作守恒。


传统策略：优先将任务调度回原核心（或超线程 sibling）以利用缓存局部性（如 Linux 调度器的 “负载均衡启发式”）。
优化方向：对于缓存敏感型工作负载（如数据库），仍需保留局部性优化；但对多数普通工作负载，应将工作守恒（快速利用空闲核心）作为更高优先级，避免因等待原核心导致整体吞吐量下降。


无需过度区分超线程 sibling 与其他空闲核心，除非能明确验证 L2 缓存保留了有效数据。
例如：当两个超线程 sibling 均空闲时，选择其中一个与选择其他物理核心的收益相近，可统一视为 “空闲资源” 处理。

有效场景：任务短时间内频繁在同一核心切换（如实时任务调度），此时 L1/L2 缓存未被显著污染，局部性收益明显。
无效场景：长时间运行的任务迁移后，原核心执行了大量其他计算，导致缓存数据完全失效。
#### idle cpu selection 
通过控制变量剥离出核心优化因子进行单独验证，验证scx_simple调度器的性能提升是否主要由“空闲核心选择策略”驱动。

实验步骤：
复制sched_ext的默认空闲核心选择函数scx_select_cpu_dfl()逻辑。
使用 BPF 将该逻辑实现为自定义函数simple_select_cpu()，并注入内核调度路径（无需依赖sched_ext框架）。
逻辑一致性：
simple_select_cpu()与scx_select_cpu_dfl()的调度逻辑完全相同（如始终优先选择完全空闲核心），确保实验仅验证 “策略本身” 而非框架差异。
验证目标：
若仅通过 BPF 复现空闲核心选择策略即可带来类似性能提升，则证明该策略是scx_simple优化的核心贡献因子，而非其他无关因素（如框架初始化开销、环境波动等）。


#### soft-affinity
尽管通过空闲核心选择实现了3.5%的性能提升，但其仅支持单一调度策略，无法处理软亲和性（Soft-affinity）、多优先级工作负载隔离等复杂需求。



#### custom policies for different threads

### scx_rusty

https://www.phoronix.com/news/Linux-6.13-Sched_Ext

https://www.phoronix.com/news/sched_ext-NUMA-Awareness


https://www.youtube.com/watch?v=CootF9OtSRM

选择几个不同的sched_ext调度类运行程序，分析差别
找到性能最好的，分析其他的调度器为什么性能不好


1. NUMA 感知的调度域优化
短期方案：在scx_rusty中添加 NUMA 节点检测逻辑，为不同 NUMA 节点的 LLC 创建独立调度域。
长期方案：整合内核的 NUMA 调度接口（如numa_get_cpu_node()），使调度域划分同时考虑 LLC 和 NUMA 拓扑。
2. 权重计算逻辑修复
问题根源：调度器假设高权重任务需独占多个核心，但实际可能通过超线程或分时复用满足需求。
修复思路：
引入 “核心需求上限”（如单个任务最多占用 N 个核心），避免过度预留。
动态调整权重与核心数的映射关系，基于历史负载数据优化分配（如使用指数平滑法预测任务实际核心需求）。
社区协同：若scx_rusty修复此问题，可将方案反馈至 CFS 社区，推动内核级权重算法改进。
3. 跨架构兼容性验证
测试重点：
在 Intel Xeon（NUMA 多 Socket）和 AMD EPYC（多 CCX 单 Socket）平台上对比scx_rusty性能，量化 NUMA 感知缺失的影响。
模拟高权重任务场景，验证修复前后的核心利用率和吞吐量变化。

调度器优化中一个常被忽视的维度：硬件架构的细微差异（如 NUMA vs. CCX）会显著影响调度策略的有效性。scx_rusty的默认设计在单 Socket 架构下表现良好，但在多 Socket 场景中因缺乏 NUMA 感知而受限，这提示调度器需更深度地融合硬件拓扑信息。

还有就是一些参数和调度逻辑，需要动态负载分析，实现更智能的资源分配。

选择几个合适的调度器，在给定的R


上周，sched_ext.git 的“for-6.13”分支中已加入一个补丁，旨在将 LLC 感知功能引入默认空闲选择策略。通过利用 Linux 内核的调度器拓扑信息，LLC 感知功能已添加到空闲选择策略中。
这使得使用内置策略的调度程序能够在具有多个 LLC 的系统（例如 NUMA 系统或基于 chiplet 的架构）中选择空闲 CPU 时做出更明智的决策，并且有助于将任务保持在同一个 LLC 域内，从而提高缓存局部性。

为了提高效率，LLC 感知仅适用于目前可以在系统所有 CPU 上运行的任务。如果从用户空间修改了任务的亲和性，则用户空间有责任选择合适的优化调度域。


Andrea Righi 也一直在努力将 NUMA 感知添加到默认空闲选择代码中。该代码仍在进行代码审查，但最新工作已于周日发布到 Linux 内核邮件列表中。该代码扩展了内置的空闲 CPU 选择策略，以便对同一 NUMA 节点内的 CPU 进行优先级排序。Righi 在该补丁中解释道：
应用此更改后，内置 CPU 空闲选择策略将遵循以下逻辑：

- 始终优先选择完全空闲的 SMT 核心中的 CPU；
- 尽可能选择相同的 CPU；
- 选择同一 LLC 域内的 CPU；
- 选择同一 NUMA 节点内的 CPU。

仅当系统具有多个 NUMA 节点或多个 LLC 域时，NUMA 和 LLC 感知功能才会启用。

未来，我们可能希望改进 NUMA 节点选择，以考虑与 prev_cpu 的节点距离。目前，该逻辑仅尝试保持任务在同一个 NUMA 节点上运行。如果节点内的所有 CPU 都处于繁忙状态，则随机选择下一个 NUMA 节点。


MySQL,PostgreSQL,Nignx,Redis(6.x+),Spark,Hadoop等
通过上游Linux内核提供的sched_ext接口或者openEuler提供的可编程调度借口实现用户态自定义调度器，实现业务亲和的自适应调度调优能力。

先选择几个已经实现的schedulers:

C实现的：
1. scx_simple
2. scx_central
3. scx_layered
4. scx_flatcg
5. scx_nest
6. scx_pair
7. scx_qmap
8. scx_prev
9. scx_userland

Rust实现的：
1. scx_bpfland
2. scx_flash
3. scx_lavd
4. scx_layered
5. scx_p2dq
6. scx_rlfifo
7. scx_rustland
8. scx_rusty
9. scx_tickless

然后再在以上实现中加入6.15的numa-aware的patch再次测试,说明numa-aware給应用带来的性能提升程度

然后如果发现特殊规律，针对特殊规律的两个应用进行调用跟踪调试

选择性能最好的5个，分析每种应用为啥性能好？
选择性能最好的2个，分析哪里还能改进？如果把numa-distance加到kernel patch中是不是效果更好？



包含NUMA感知的调度器

6.13 对 Sched_EXT 的一个非常有用的新增功能是引入了 LLC 和 NUMA 感知。Sched_EXT 现在可以在多路服务器等的 NUMA 环境中更好地运行。最后一级缓存 (LLC) 感知还可以增强当今基于小芯片的处理器（例如 AMD Ryzen 和 AMD EPYC Linux 系统）的空闲 CPU 检测逻辑。这些 Linux 6.13 新增功能将有助于在同一个 LLC 域中选择 CPU 内核，然后是 NUMA 节点

Linux 6.13 中的 sched_ext 代码还能更好地处理 WAKE_SYNC，修复了多路 Intel Xeon Sapphire Rapids 服务器上跨路对同一队列进行锤击操作可能导致系统实时锁定的问题，并提高了“调度”和“使用”术语的清晰度。


https://www.phoronix.com/news/Linux-6.13-Sched_Ext

https://www.phoronix.com/news/sched_ext-NUMA-Awareness


https://lore.kernel.org/lkml/20241027174953.49655-1-arighi@nvidia.com/

https://git.kernel.org/pub/scm/linux/kernel/git/tj/sched_ext.git/commit/?h=for-6.13&id=dfa4ed29b18c5f26cd311b0da7f049dbb2a2b33b

https://git.kernel.org/pub/scm/linux/kernel/git/tj/sched_ext.git/log/?h=for-6.13


Nginx性能测试:
https://plantegg.github.io/2022/10/10/Nginx%E6%80%A7%E8%83%BD%E6%B5%8B%E8%AF%95/


https://developer.aliyun.com/article/475489

现在直接编译的是x86的kernel，如果想在arm架构上运行，要先考虑使用qemu模拟arm的架构，然后挂载文件系统，在上面再运行对应的os进行应用测试，但是如果在虚拟机中运行，估计会很卡，多层嵌套了。

考虑租一个ubuntu服务器然后再在上面运行arm架构的内容，少了一层虚拟机，然后可以做成镜像，这样可以compile once run anywhere

但是x86架构下也可以启动sched_scx,先用CFS或者EEVDF测试一下redis的性能，然后在开启sched_ext测试redis的性能。

写成一个测试脚本
redis的性能应该用ycsb-load来测试，直接将之前服务器上的拷贝过来运行。

然后换成arm的环境，qemu配置的环境尽量符合鲲鹏920的环境，但是os不想选openEuler，还是用Linux kernel的arm架构编译一下。

然后就是分析一下提供的几个应用，都有什么特点

然后是numa balancing怎么改呢？

最后是内存分配器的原理

ptmalloc的原理


