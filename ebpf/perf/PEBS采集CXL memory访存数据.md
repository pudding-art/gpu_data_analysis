## PEBS采集CXL memory访存数据



![image-20240720153412576](/Users/hong/Library/Application%20Support/typora-user-images/image-20240720153412576.png)

dram的read和write带宽估计事件可以参考上面的事件，上面涉及interference estimation部分的pending queue相关的内容，可以找一下DRAM和CXL Memory是否有相关的。

参考pcm-tools中的pcm-memory中对CXL bandwidth的监控代码，找到以下可用事件：

![image-20240720155505914](/Users/hong/Library/Application%20Support/typora-user-images/image-20240720155505914.png)

1. cross-NUMA

2. LLC misses

3. load/store

4. pending queues

5. uncore PMU events related to CXL

   •CXLCM_TxC_PACK_BUF_INSERTS.MEM_DATA(Write)

   •UNC_CHA_TOR_INSERTS.IA_MISS_CRDMORPH_CXL_ACC(Read)

   •UNC_CHA_TOR_INSERTS.IA_MISS_RFO_CXL_ACC(Read)

   •UNC_CHA_TOR_INSERTS.IA_MISS_DRD_CXL_ACC(Read)

   •UNC_CHA_TOR_INSERTS.IA_MISS_LLCPREFRFO_CXL_ACC(Read)

先找以上相关的pebs events

![image-20240720155904595](/Users/hong/Library/Application%20Support/typora-user-images/image-20240720155904595.png)

![image-20240720155909616](/Users/hong/Library/Application%20Support/typora-user-images/image-20240720155909616.png)

![image-20240720155914952](/Users/hong/Library/Application%20Support/typora-user-images/image-20240720155914952.png)

- [ ] 找到相关的events之后也像Table1一样列一个表，包括event的名称，地址，描述，以及用处

源码下载方式：https://blog.csdn.net/qq_43257914/article/details/134344756

perf_events是Linux上广泛使用的profiling/tracing工具，除了本身是kernel组成部分，还有用户空间的使用工具(perf-terminal-tools)。是内核对用户态提供软硬件性能数据的一个统一的接口，用户通过 perf_event 的句柄操作能获取到各式各样的性能数据。

perf_events两种工作模式：

\- 采样模式sampling：周期性做事件采样，并将信息记录下来，默认保存perf.data文件，eg: `perf record`

\- 计数模式counting：仅统计某事件发生的次数，eg: `perf stat`

perf_events所处理hardware event需要CPU的支持（这里还有一些software event之类的），目前主流CPU基本都包含了PMU（用来统计性能相关的参数，这些统计工作由硬件完成，CPU开销小）

事件来源：硬件事件、软件事件、内核追踪点事件、USDT、动态追踪、时序剖析

https://juejin.cn/post/7221495028031307836

**PMU, MSR, PEBS, PMC概念区分**

\- PMU(Performance Monitoring Unit)：统计性能相关的参数，由MSRs组成

\- MSR(Model-Specific Registers)：称为Model-Specific是因为不同model的CPU，有些regs是不同的，有2种MSRs，一种叫PEBS，一种叫PMC

\- PEBS(Performance Event Select Registers)：MSR的一种，想对某种性能事件Performance Event进行统计时，需要对PEBS进行设置

\- PMC(Performance Monitoring Counters)：统计某种性能事件并对PEBS设置后，统计结果会保存在PMC中

 当perf_*events工作在采样模式（sampling，perf record命令即工作在这种模式）时，由于采样事件发生时和实际处理采样事件之间有时间上的delay，以及CPU流水线和乱序执行等因素，所以**得到的指令地址IP(Instruction Pointer) 并不是当时产生采样事件的IP，这个称之为skid**。为了改善这种状况，使IP值更加准确，Intel使用PEBS（Precise Event-Based Sampling），而AMD则使用IBS（Instruction-Based Sampling）。*以PEBS为例：每次采样事件发生时，会先把采样数据存到一个缓冲区中（PEBS buffer），当缓冲区内容达到某一值时，再一次性处理，这样可以很好地解决skid问题。

两种实现方式，一个是直接写到内核代码中，然后编译内核源码，另一种方法是使用动态编译加载Linux内核模块的方法。

### 方法一

![image-20240720160945659](/Users/hong/Library/Application%20Support/typora-user-images/image-20240720160945659.png)



需要修改以上文件的代码，参考：https://github.com/cosmoss-jigu/memtis/commit/44622b675df1538dc6111b7ee8ddb4fea365d5c2



#### arch/x86/entry/syscalls修改，在syscall_64.tbl中添加系统调用函数

arch/x86/entry/syscalls注册新加函数的系统调用。Linux x86_64系统调用简介：https://evian-zhang.github.io/introduction-to-linux-x86_64-syscall/

所有的系统调用列表位于Linux内核源码的arch/x86/entry/syscall_64.tbl中，注意当前Linux内核的版本和glibc的版本。大概结构如下，如要包括文件系统的系统调用以及内存管理相关的系统调用：

<img src="/Users/hong/Library/Application%20Support/typora-user-images/image-20240720161304638.png" alt="image-20240720161304638" style="zoom:50%;" />



在Linux系统中，内核提供一些操作的interface给用户态的程序使用，即系统调用。对于用户态的程序，其调用相应的interface的方式，是一条汇编指令syscall。比如说，创建子进程的操作，Linux内核提供了`fork`这个系统调用作为接口。那么，如果用户态程序想调用这个内核提供的接口，其对应的汇编语句为（部分）

```x86asm
movq $57, %rax
syscall
```

`syscall`这个指令会先查看此时RAX的值，然后找到系统调用号为那个值的系统调用，然后执行相应的系统调用。我们可以在系统调用列表中找到，`fork`这个系统调用的系统调用号是57。于是，我们把57放入`rax`寄存器中，然后使用了`syscall`指令。这就是让内核执行了`fork`。

增加以下内容：

![image-20240720180235685](/Users/hong/Library/Application%20Support/typora-user-images/image-20240720180235685.png)

- [ ] perf的基本知识看一下，如何在kernel中使用确认
- [ ] memtis的pebs采集逻辑看懂

#### include/linux中添加embm头文件以及对perf_event和syscall头文件进行修改

`syscalls.h:`

![image-20240722233442157](/Users/hong/Library/Application%20Support/typora-user-images/image-20240722233442157.png)

`perf_event.h:`

![image-20240722233520820](/Users/hong/Library/Application%20Support/typora-user-images/image-20240722233520820.png)



perf内核源码重要数据结构perf_event, 重要文件include/linux/perf_event.h和/kernel/events/core.c，首先 要了解大概流程，然后要仔细阅读代码才能了解整体的实现。

perf在user space, kernel space和hardware的实现要清楚才能进行下一步内容：

![image-20240722210113900](/Users/hong/Library/Application%20Support/typora-user-images/image-20240722210113900.png)

以上是perf调用的原理图。用户态触发`sys_perf_event_open()`系统调用，内核陷入中断以后会调用`perf_event_open`来处理，该函数位于`kernel/events/core.c`文件下。`perf_event_open`会负责初始化计数器相关，并去获得相关的数据。这些数据会被放到ring-buffer中等待用户态读取。

如果只想在kernel space实现perf数据采集的流程，就只需要中间红色部分的内容，使用perf_mmap分配数据存储空间，使用perf_event_open开启硬件对相应事件的计数。(实际上就是core.c的内容)

```c
/**
 * sys_perf_event_open - open a performance event, associate it to a task/cpu
 *
 * @attr_uptr:  event_id type attributes for monitoring/sampling
 * @pid:        target pid
 * @cpu:        target cpu
 * @group_fd:   group leader event fd
 * @flags:      perf event open flags
 */
SYSCALL_DEFINE5(perf_event_open,
        struct perf_event_attr __user *, attr_uptr,
        pid_t, pid, int, cpu, int, group_fd, unsigned long, flags)

```

通过SYSCALL_DEFINE5来定义对应的open函数事件和参数

很重要的一些perf内核参数：

```c++
    struct perf_event *group_leader = NULL, *output_event = NULL;
    struct perf_event_pmu_context *pmu_ctx;
    struct perf_event *event, *sibling;
    struct perf_event_attr attr;
    struct perf_event_context *ctx;
    struct file *event_file = NULL;
    struct fd group = {NULL, 0};
    struct task_struct *task = NULL;
    struct pmu *pmu;
    int event_fd;
    int move_group = 0;
    int err;
    int f_flags = O_RDWR;
    int cgroup_fd = -1;
```

由于perf_event_open是一个系统调用，如果直接在用户态给系统调用传参是不会直接传递过来的，需要通过一些特定的函数进行参数的传递，如：

```c
    err = perf_copy_attr(attr_uptr, &attr); // L12337
    if (err)
        return err;
```

作为一个系统调用，而且是非常关键、可能有追踪的系统调用，有必要进行一些权限检查：

```c
/* Do we allow access to perf_event_open(2) ? */
// L12341
    err = security_perf_event_open(&attr, PERF_SECURITY_OPEN);
    if (err)
        return err;
​
    if (!attr.exclude_kernel) {
        err = perf_allow_kernel(&attr);
        if (err)
            return err;
    }
​
    if (attr.namespaces) {
        if (!perfmon_capable())
            return -EACCES;
    }
​
    if (attr.freq) {
        if (attr.sample_freq > sysctl_perf_event_sample_rate)
            return -EINVAL;
    } else {
        if (attr.sample_period & (1ULL << 63))
            return -EINVAL;
    }
​
    /* Only privileged users can get physical addresses */
    if ((attr.sample_type & PERF_SAMPLE_PHYS_ADDR)) {
        err = perf_allow_kernel(&attr);
        if (err)
            return err;
    }

```

然后开始分配和初始化事件结构体：

```c
// L 12423  
event = perf_event_alloc(&attr, cpu, task, group_leader, NULL,
                 NULL, NULL, cgroup_fd);
    if (IS_ERR(event)) {
        err = PTR_ERR(event);
        goto err_task;
    }
​
    if (is_sampling_event(event)) {
        if (event->pmu->capabilities & PERF_PMU_CAP_NO_INTERRUPT) {
            err = -EOPNOTSUPP;
            goto err_alloc;
        }
    }

```

这里的event是perf_event类型的，具体定义在/include/linux/perf_event.h目录下：

```c
/**
 * struct perf_event - performance event kernel representation:
 */
struct perf_event {
#ifdef CONFIG_PERF_EVENTS
    /*
     * entry onto perf_event_context::event_list;
     *   modifications require ctx->lock
     *   RCU safe iterations.
     */
    struct list_head        event_entry;
​
    /*
     * Locked for modification by both ctx->mutex and ctx->lock; holding
     * either sufficies for read.
     */
    struct list_head        sibling_list;
    struct list_head        active_list;
    /*
     * Node on the pinned or flexible tree located at the event context;
     */
 ...

```

然后会去获取目标上下文信息并保存到类型为perf_event_context, perf_event_pmu_context变量中：

```c
    /*
     * Get the target context (task or percpu):
     */
    ctx = find_get_context(task, event); // L12468
    if (IS_ERR(ctx)) {
        err = PTR_ERR(ctx);
        goto err_cred;
    }
    pmu_ctx = find_get_pmu_context(pmu, ctx, event); // L 12568
    if (IS_ERR(pmu_ctx)) {
        err = PTR_ERR(pmu_ctx);
        goto err_locked;
    }
```

之后，通过anon_inode_getfile创建文件，该文件会通过最后的fd_install和进程相关联起来：

```c
    // L 12602
    event_file = anon_inode_getfile("[perf_event]", &perf_fops, event, f_flags);
    if (IS_ERR(event_file)) {
        err = PTR_ERR(event_file);
        event_file = NULL;
        goto err_context;
    }
​
    //L 12676
    /*
     * Drop the reference on the group_event after placing the
     * new event on the sibling_list. This ensures destruction
     * of the group leader will find the pointer to itself in
     * perf_group_detach().
     */
    fdput(group);
    fd_install(event_fd, event_file);
    return event_fd;

```

最后，函数会通过perf_install_in_context将上下文和性能事件进行绑定，并调用相关函数访问性能计数器：

```c
	 // L 12651
     /*
	 * Precalculate sample_data sizes; do while holding ctx::mutex such
	 * that we're serialized against further additions and before
	 * perf_install_in_context() which is the point the event is active and
	 * can use these values.
	 */
	perf_event__header_size(event);
	perf_event__id_header_size(event);

	event->owner = current;

	perf_install_in_context(ctx, event, event->cpu);
	perf_unpin_context(ctx);

	mutex_unlock(&ctx->mutex);

	if (task) {
		up_read(&task->signal->exec_update_lock);
		put_task_struct(task);
	}

	mutex_lock(&current->perf_event_mutex);
	list_add_tail(&event->owner_entry, &current->perf_event_list);
	mutex_unlock(&current->perf_event_mutex);

```



syscalls.h文件，主要是为了用户态调试，定义的系统调用文件，添加系统调用流程如下：

1. 添加系统调用头文件, 在include/linux/syscalls.h文件中的#endif前添加自己的系统调用函数声明，如下：

   ```c
   asmlinkage long sys_embm_start(pid_t pid, int node);
   asmlinkage long sys_embm_end(pid_d pid);
   ```

2. 添加系统调用实现源码

   随便中啊一个文件，在文件中添加系统调用的源码SYSCALL_DEFINEn(xx)

   SYSCALL_DEFINE1是系统调用的入口，其中1表示函数参数的个数，name表示系统调用函数的名字，同理下面的2,3,4,5,6表示参数个数，定义在include/linux/syscalls.h中。

   ```c
   #ifndef CONFIG_EMBM
   SYSCALL_DEFINE2(embm_start,
   		pid_t, pid, int, node)
   {
       return 0;
   }
   
   SYSCALL_DEFINE1(embm_end,
   		pid_t, pid)
   {
       return 0;
   }
   #else
   SYSCALL_DEFINE2(embm_start,
   		pid_t, pid, int, node)
   {
     	ksamplingd_init(pid, node);
       return 0;
   }
   
   SYSCALL_DEFINE1(embm_end,
   		pid_t, pid)
   {
     	ksamplingd_init(pid);
       return 0;
   }
   ```

3. 在系统调用表中添加相应的表项

   添加系统调用向量，在***\*arch/x86/syscalls/syscall_64.tbl\****文件中添加系统调用号和系统调用服务程序入口（如果是32位系统，则修改syscall_32.tbl文件）

   <img src="/Users/hong/Library/Application%20Support/typora-user-images/image-20240722232859254.png" alt="image-20240722232859254" style="zoom:50%;" />

   系统调用会去查找`sys_call_table`这个数组并找到对应的系统调用函数去执行，注意其中有一个关键函数`do_ni_syscall`，(no implement syscall),当**<u>系统调用遇到一些限制或者问题</u>**时会跳转到该函数去执行。

   ```c
   arch/arm64/kernel/sys.c:
   /*
    * The sys_call_table array must be 4K aligned to be accessible from
    * kernel/entry.S.
    */
   void * const sys_call_table[__NR_syscalls] __aligned(4096) = {
       [0 ... __NR_syscalls - 1] = sys_ni_syscall,
   #include <asm/unistd.h>
   };
   ```

   这个数组在创建时首先会把所有的数组成员设置为`sys_ni_syscall`，而后根据`asm/unistd.h`中的内容做进一步初始化。其实最终该头文件会把`include/uapi/asm-generic/unistd.h`包含进来，也就是这个头文件会是最终定义数组的地方。如下所示:

   ```c
   __SYSCALL(__NR_bpf, sys_bpf)
   #define __NR_execveat 387
   __SYSCALL(__NR_execveat, compat_sys_execveat)
   #define __NR_userfaultfd 388
   __SYSCALL(__NR_userfaultfd, sys_userfaultfd)
   #define __NR_membarrier 389
   __SYSCALL(__NR_membarrier, sys_membarrier)
   #define __NR_mlock2 390
   __SYSCALL(__NR_mlock2, sys_mlock2)
   #define __NR_copy_file_range 391
   __SYSCALL(__NR_copy_file_range, sys_copy_file_range)
   #define __NR_preadv2 392
   __SYSCALL(__NR_preadv2, compat_sys_preadv2)
   #define __NR_pwritev2 393
   __SYSCALL(__NR_pwritev2, compat_sys_pwritev2)
   ```

   添加系统调用之后也需要在此数组中添加一个元素，例：

   ```cpp
   #define __NR_test 394
   __SYSCALL(__NR_test, sys_test)
   ```

   在数组中添加元素之后，还需要更新这个数组元素的个数:

   ```c
   arch/arm64/include/sam/unistd.h
   #define __NR_compat_syscalls 395//394+1
   ```

4. 添加系统调用号

   在unistd.h的文件中，每个系统调用号都已_NR_开头，我们添加系统调用号如下所示:

   ```c
   #define __NR_test 290
   __SYSCALL(__NR_test,     sys_test)
    
   #undef __NR_syscalls
   #define __NR_syscalls 292//291+1
   ```

5. 应用测试程序

   ```c
   #include <linux/unistd.h>
   #include <sys/syscall.h>
   #include <stdio.h>
    
   int main(void)
   {
           long ret= syscall(290);
           printf("%s %d ret = %d\n", __func__,__LINE__,ret);
    
           return 0;
   }
   ```

-----

perf_event资源如何在内核中呈现、运行，会依次如何对硬件进行操作，如何产生分时复用，以及在软件层面如何产生影响。

perf_event：代表一种事件资源，用户态调用 perf_open_event 即会创建一个与之对应的 perf_event 对象，相应的一些重要数据都会以这个数据结构为维度存放 包含 pmu ctx enabled_time running_time count 等信息。

pmu：代表一种抽象的软硬件操作单元，它可以是 cpu，software，在 cpu 的实现下，它负责对硬件 PMC/PERFEVTSEL/FIXED_CTR/FIXED_CTR_CTRL 进行操作。每一种厂商在内核实现的 pmu 是不同的。在内核中 PMCx 与 PERFEVTSELx 属于 cpu pmu，而 RDT 属于 intel_cqm pmu。pmu 包含一系列方法（以 perf_event 为输入参数），用于 初始化/关闭/读取 硬件pmu设备，cpu 就是一个 pmu，这一个对象包含了所有的 cpu 硬件事件。它是一个类对象（可以认为是单例实现），全局共享，由 attr.type 来定位，开机时内核会注册一系列（arch/x86/kernel/cpu/perf_event.c）pmu 放置 pmu_idr 中，它会实现一系列对硬件操作和状态管理函数，如enable，disable，add，del。同时分时复用的一些分配通用 pmc 的逻辑也在里面。

perf_event_context：代表 perf_event 和 pmu 的一种抽象，它会包含 perf_event_list 和 pmu。是 perf_event 子系统操作的最小单元。它会被包含在 task 或 cpu 结构中，这样一来与其他子系统如 sched 产生协作。perf_event_context 是 perf_event 的一个 container, 以列表的方式维护多个perf_event对象，ctx 包含 perf_event 后以 task 和 cpu 两个维度维护，per-cpu 对象中会包含 context（当指定 per-cpu event的时候，会alloc context 并赋值到p er-cpu 数组中），同样 task 的结构对象中也会包含 context，这两者用sched_switch 时会判断 context 中的内容作出决定



### 事件作用域

perf_event 系统调用中提供两种维度的作用域

1. task
2. cpu

在内核中将 event 分为 per-task 和 per-cpu, 还有一种 per-cgroup，它实际上是 per-task 类型的

如果是 per-task 它会将 perf_context 分配到 task struct 中

如果是 per-cpu 它会将 perf_context 分配到一个全局 per_cpu 变量中



**参考文献：**

【1】核心调用，perf_event_open: https://juejin.cn/post/7224121578124181562

【2】Linux添加一个系统调用syscall原理：https://blog.csdn.net/qq_37600027/article/details/104287857

【3】SYSCALL_DEFINEx宏源码解析：https://blog.csdn.net/qq_41345173/article/details/104071618

【4】perf event内核篇：https://blog.csdn.net/weixin_33756418/article/details/89720185 主要关注**内核性能分析（开销）的部分**



#### kernel/events中修改core.c文件





#### mm中修改Makefile和embm_sampler.c文件



perf_event_attr: https://man7.org/linux/man-pages/man2/perf_event_open.2.html



### 方法二

- [ ] 内核模块机制复习一下，如何动态加载模块















---------------

1. /sys/fs/cgroup/cpu/cpu_limited/cpu.stat 查看cfs_quota_ns设置的信息是否正确；
2. 尝试不同的`cfs_quota_us`和`cfs_period_us`值，找到最佳的配置;
3. 使用其他内存带宽测试工具，例如`sysbench`或`fio`，来验证CXL内存的性能;

1. **安装fio**： 如果你的系统中还没有安装`fio`，可以通过包管理器安装它。例如，在基于Debian的系统上，你可以使用以下命令安装：

   ```
   bash
   sudo apt-get install fio
   ```

2. **准备测试配置文件**： `fio`需要一个配置文件来指定测试的参数。以下是一个简单的配置文件示例，用于测试读、写和随机访问模式的带宽：

   ```
   bash
   [global]
   ioengine=sync
   direct=1
   size=1G
   runtime=60
   time_based=1
   
   [read]
   rw=read
   
   [write]
   rw(write)
   
   [randread]
   rw=randread
   
   [randwrite]
   rw=randwrite
   ```

3. **选择正确的ioengine**： 对于内存测试，`ioengine`参数应该设置为`sync`或`libaio`，这取决于你的系统配置和偏好。

4. **设置direct参数**： 设置`direct=1`来启用直接I/O，这样测试就不会受到缓存的影响。

5. **定义测试作业**： 在配置文件中定义不同的作业，例如`[read]`、`[write]`、`[randread]`和`[randwrite]`，分别对应顺序读、顺序写、随机读和随机写。

6. **运行fio测试**： 使用以下命令运行`fio`测试，并指定配置文件：

   ```
   bash
   fio your_test_config.fio
   ```

   这将执行配置文件中定义的所有作业，并输出每个作业的带宽和延迟结果。

7. **分析结果**： `fio`会输出每个测试作业的详细结果，包括带宽（以MB/s为单位）、IOPS和延迟（以微秒为单位）。

8. **调整测试参数**： 根据需要调整配置文件中的`size`（测试的总数据量）、`runtime`（每个作业的运行时间）和其他参数，以获得更准确的测试结果。

9. **多线程测试**： 如果需要测试多线程性能，可以在配置文件中添加`thread`作业，并设置`numjobs`参数来指定并发作业的数量。

10. **内存节点绑定**： 如果测试CXL内存，确保`fio`作业绑定到正确的内存节点。可以使用`numactl`命令来实现这一点：

    ```
    bash
    numactl --membind=<memory_node> fio your_test_config.fio
    ```

    其中`<memory_node>`应该替换为你想要绑定的内存节点编号。

请注意，`fio`默认使用文件系统进行测试，如果要直接测试内存带宽，需要确保测试的数据在内存中，或者使用CXL内存设备作为测试的目标。如果CXL内存被配置为内存的一部分，`fio`可能需要直接对CXL内存设备进行操作，这通常需要特定的配置和权限。





-----

### 修改测试程序

这些步骤适用于 cgroup v2。如果你使用的是 cgroup v1，路径和命令可能会有所不同。确保你有足够的权限来创建和修改 cgroup 设置，并运行测试程序。

```shell
cgroup:sudo cgcreate -g cpu:my_cgroup;

for quota in 10000 20000 30000 40000 50000 60000 70000 80000 90000 100000; do
    echo $quota > /sys/fs/cgroup/cpu/my_cgroup/cpu.cfs_quota_us
    # 运行你的性能测试
    # 收集结果
done

# 之前是直接写入到cgroup的procs中，现在换另外一种方式测试一下
sudo cgclassify -g cpu:my_cgroup <PID_of_your_test_program>
```

由于cpulimit限制进程内存CPU time的方法和cgroup一致，虽然原理不一致，但是最终都达到限制CPU time的效果，而我们这里也只是从限制CPU time的效果开始再进行对应用的读写带宽影响研究，所以这里可以用cpulimit代替。

```shell
sudo apt-get install cpulimit

# 直接在limit下运行
cpulimit -l 50 python test.py # -l 后面跟的是cpu利用率上限 
# 先启动程序再根据进程号PID在limit下运行
cpulimit -l 50 -p 1234 # 50是cpu利用率，1234是进程号
```







echo 出现报错 invalid argumen

















