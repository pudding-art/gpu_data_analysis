perf_events是Linux上广泛使用的profiling/tracing工具，除了本身是kernel组成部分，还有用户空间的使用工具(perf-terminal-tools)。是内核对用户态提供软硬件性能数据的一个统一的接口，用户通过 perf_event 的句柄操作能获取到各式各样的性能数据。

perf_events两种工作模式：

- 采样模式sampling：周期性做事件采样，并将信息记录下来，默认保存perf.data文件，eg: `perf record`
- 计数模式counting：仅统计某事件发生的次数，eg: `perf stat`

perf_events所处理hardware event需要CPU的支持（这里还有一些software event之类的），目前主流CPU基本都包含了PMU（用来统计性能相关的参数，这些统计工作由硬件完成，CPU开销小）

**PMU, MSR, PEBS, PMC概念区分**

- PMU(Performance Monitoring Unit)：统计性能相关的参数，由MSRs组成

- MSR(Model-Specific Registers)：称为Model-Specific是因为不同model的CPU，有些regs是不同的，有2种MSRs，一种叫PEBS，一种叫PMC

- PEBS(Performance Event Select Registers)：MSR的一种，想对某种性能事件Performance Event进行统计时，需要对PEBS进行设置

- PMC(Performance Monitoring Counters)：统计某种性能事件并对PEBS设置后，统计结果会保存在PMC中

  > [!NOTE]
  >
  > 当perf_events工作在采样模式（sampling，perf record命令即工作在这种模式）时，由于采样事件发生时和实际处理采样事件之间有时间上的delay，以及CPU流水线和乱序执行等因素，所以**得到的指令地址IP(Instruction Pointer) 并不是当时产生采样事件的IP，这个称之为skid**。为了改善这种状况，使IP值更加准确，Intel使用PEBS（Precise Event-Based Sampling），而AMD则使用IBS（Instruction-Based Sampling）。
  >
  > 以PEBS为例：每次采样事件发生时，**会先把采样数据存到一个缓冲区中（PEBS buffer）**，当缓冲区内容达到某一值时，再一次性处理，这样可以很好地解决skid问题。

  ![image-20240626105247841](C:\Users\user\AppData\Roaming\Typora\typora-user-images\image-20240626105247841.png)

系统调用perf_open_event，还是在用户态中使用，代表一种事件资源，用户态调用perf_open_event会创建一个与之对应的perf_event对象，相应的一些重要数据会放在这个数据结构中。

```c
//running_time count 等信息
include/linux/perf_event.h
struct perf_event {

}
//./arch/arm64/kernel/perf_event.c

//perf stat实现
tools/perf/builtin-stat.c
run_perf_stat
   __run_perf_stat

print_stat
```

perf开销，可以通过perf本身监控perf进程来确定。

```shell
# perf进程获取
ps -eo pmem,pcpu,args   | grep perf  | grep -v grep
# 开销采集，使用越多参数，开销越大
perf stat -e syscalls:* -p 49770 sleep 10
```

<img src="C:\Users\user\AppData\Roaming\Typora\typora-user-images\image-20240626110120774.png" alt="image-20240626110120774" style="zoom:50%;" />

看前面的performance最后稳定的比例。

----

记录内存访问样本数量的变化，需要对PEBS计数器进行编程。

**请不要在单次运行**中混合使用跟踪和时序测量。

最快地运行Spec和跟踪所有内存访问都是不可能的。一次运行用于计时，另一次(更长，更慢)进行内存访问跟踪。



pmu-tools ocperf.py 简化Intel event名称的编码

[pmu-tools/ocperf.py at master · andikleen/pmu-tools · GitHub](https://github.com/andikleen/pmu-tools/blob/master/ocperf.py)



![image-20240626112026271](C:\Users\user\AppData\Roaming\Typora\typora-user-images\image-20240626112026271.png)







![image-20240626112119238](C:\Users\user\AppData\Roaming\Typora\typora-user-images\image-20240626112119238.png)

[linux/tools/perf/Documentation/perf-intel-pt.txt at master · torvalds/linux · GitHub](https://github.com/torvalds/linux/blob/master/tools/perf/Documentation/perf-intel-pt.txt)



Intel Processor Trace

[libipt/ptdump/src/ptdump.c at master · intel/libipt · GitHub](https://github.com/intel/libipt/blob/master/ptdump/src/ptdump.c)

Intel PT使用Manual

[Cheat sheet for Intel Processor Trace with Linux perf and gdb at Andi Kleen's blog (halobates.de)](https://halobates.de/blog/p/410)

![image-20240626112813977](C:\Users\user\AppData\Roaming\Typora\typora-user-images\image-20240626112813977.png)



开销分析：

![image-20240626113328962](C:\Users\user\AppData\Roaming\Typora\typora-user-images\image-20240626113328962.png)



---

### 如何通过用户态实现对内核 perf_event 功能的使用

```c
int perf_event_open(struct perf_event_attr *attr, //事件类型以及参数 （attr.type attr.config）
                    pid_t pid, int cpu, int group_fd, //被监控的进程 或者 cgroup,cpu id,perf 事件组
                    unsigned long flags); //man perf_event_open

//1.对创建的 event 句柄控制,主要是通过 ioc 和 prctl
ioc(fd, PERF_EVENT_IOC_DISABLE, 0) //暂停该事件的监控
ioc(fd, PERF_EVENT_IOC_RESET, 0) // 重置计数器
    
    
    
// 完整code
# 创建 event 属性
cycle_perf_event_attr = pyperf.perf_event_attr()
cycle_perf_event_attr.type = pyperf.PERF_TYPE_HARDWARE # 通用 CPU 事件类型
cycle_perf_event_attr.config = pyperf.PERF_COUNT_HW_CPU_CYCLES # 记录 CPU cycle
cycle_perf_event_attr.inherit = 1

# 其他参数
cpu = -1 # 所有cpu
pid = 0 # 监控本进程

# 打开事件
fd = pyperf.perf_event_open(cycle_perf_event_attr, pid, cpu, -1, flag)

time.sleep(1)
ret = os.read(fd, 8) # 所有字段均为 64 bit
value = struct.unpack("L", ret)[0]
```

**multiplexing (多路复用)**:

- 在`perf_events`中，`multiplexing`是指能够**同时监控多个CPU或多个进程的性能事件**的能力。当启用`multiplexing`时，你可以收集来自不同CPU或不同进程的性能数据，并将它们汇总到一个单一的计数器中。这在分析分布式系统或多进程应用的性能时非常有用当你使用`perf_event_open`并传递`-1`作为CPU参数时，这可能意味着你想要在所有CPU上监控事件。如果`multiplexing`被启用，`perf_events`将能够收集来自所有这些CPU的性能数据，并将它们汇总到一个计数器中

- **core**: 指的是CPU核心内部的事件，如指令周期、分支指令等，在系统中查看 /proc/cpuinfo 看到的最小核（逻辑核），core 事件是最好理解的，即是跟逻辑核完全绑定的事件，如该核运行的 cycle 和 instruction 次数
- **offcore**: 由两个（或者多个兄弟逻辑核）共享的一些事件，比如访问内存，因为在硬件上它们走的是同一个通道。本质上，它是一个 core 事件，但需要额外配置
- **uncore**: 在物理核的层面上又有一部分资源是物理核共享的（同时也就是 cpu socket 的概念），比如 LLC 是一个 socket 共享，这部分资源被划分为 uncore。uncore 较为复杂，它不在是以 core 为视角采集性能事件，而是通过在共享资源如 LLC 的视角对接每个 core 设备时提供各式各样的 Box。再拿 LLC 举例子，LLC 提供若干 CBox 为每个 core 提供服务。因此 uncore 事件要建立在 CBox 元件上

----

### 硬件 PMU 如何为 linux kernel perf_event 子系统提供硬件性能采集功能 

<!--硬件 PMU 的实现就是提供了一系列的可操作 MSR， 通过 MSR 操作可以灵活定义要监控的内容，但是 linux kernel 中通过实现 perf_event 子系统对用户态提供了一套简洁通用的操作界面-->

汇编指令 rdmsr/wrmsr

```
wrmsr 0x38d 1234 # addr value
```

如果是 pmc 还可以用 rdpmc 指令

```
rdpmc [0~7] # input ECX output EDX:EAX
```

在硬件 pmu 的操作过程中大多类似以下模式

1. **写入 pmc 对应的状态 msr，决定要打开哪个硬件事件**
2. **通过读取 pmc 获取之前定义的硬件事件数值**

----

三种事件捕捉实现：
**PMCx 与 PERFEVTSELx**

**通用事件**寄存器，成对出现，由 PERFEVTSEL 配置事件，PMC 读取事件数值。在现代 x86 产品中被称之为通用 pmu 设备，一般为4个，如果关闭虚拟化可以使用8个

**FIXED_CTRx 与 FIXED_CTR_CTRL**

**专用**寄存器，通过唯一的 FIXED_CTR_CTRL 来开启对应的 FIXED_CTRx。无事件控制，每个 FIXED_CTRx 只能记录对应的硬件事件

RDT （Resource Direct Tech） 是一种全新的性能采集方式，有点与上述两种寄存器有所不同，但是在软件接口上会更简洁。支持 L3 cache 相关资源使用计数

它的操作过程不用定义事件类型，只要以下步骤

1. **通过 PQR_ASSOC msr寄存器写入 rmid 就已经开始统计相关事件的计数**
2. **通过QM_EVTSEL 输入要读取的事件 id 和 rmid**
3. **最后通过 QM_CTR 即可获得数据**

可以看出它不再以单独的CPU为维度，用户可以自定义 rmid，可以用 task，也可以用 cpuid，甚至多者混合

----

##### 说明

`PERFEVTSELx`（Performance Event Select Registers）

1. **PMCx (Performance Monitoring Counters)**:
   - 这些是实际用于计数的寄存器，它们记录了特定事件发生的次数。例如，一个PMC可能被配置为计数指令的执行次数或缓存未命中的次数。
   - 通常，每个核心有多个PMC寄存器，允许同时监控多个事件。
2. **PERFEVTSELx (Performance Event Select Registers)**:
   - 这些寄存器用于选择和配置PMC寄存器将要监控的事件。每个`PERFEVTSELx`寄存器对应一个PMC寄存器。
   - 通过编程`PERFEVTSELx`寄存器，可以设置要监控的事件类型、事件的UMASK（用于进一步过滤事件的条件）、用户/内核模式等属性。

`PERFEVTSELx`寄存器的配置通常包括以下几个方面：

- **Event Select**: 指定要监控的事件代码。
- **UMASK**: 用于过滤事件的位掩码，可以指定监控特定类型的事件。
- **User/Kernel**: 指定事件是否在用户模式、内核模式或两者都计数。
- **Invert**: 可以选择性地反转事件的计数逻辑。
- **Enable**: 启用或禁用计数器。



在RDT中，`rmid`（Resource Monitoring Identifier）是一个关键概念，它用于标识特定的资源监控实体。每个`rmid`都与一个特定的资源池或资源监控组相关联。在使用RDT时，你可以通过以下步骤进行操作：

1. **通过PQR_ASSOC MSR（Model-Specific Register）写入rmid**:
   - PQR_ASSOC MSR用于将逻辑处理器（如线程）与一个特定的`rmid`关联起来。一旦关联，该逻辑处理器的资源使用情况将被监控并计入与`rmid`相关联的资源池。
2. **通过QM_EVTSEL配置监控事件**:
   - QM_EVTSEL是RDT中的一个配置寄存器，用于选择要监控的事件类型。与PMCx和PERFEVTSELx不同，RDT可能不需要定义事件类型，而是直接选择要监控的资源。
3. **通过QM_CTR读取数据**:
   - QM_CTR是RDT中的一个计数器寄存器，用于读取与`rmid`相关联的资源使用计数。这个计数器将提供关于逻辑处理器使用特定资源的详细信息。

`rmid`的使用允许RDT技术跨多个逻辑处理器和多个资源池进行细粒度的资源监控和分配。例如，在L3缓存监控的场景中，你可以为不同的应用程序或服务分配不同的`rmid`，然后通过RDT监控它们对L3缓存的使用情况。

----

linux 系统提供了 msr 内核模块，允许用户可以在用户态直接操作 msr

```
ls /dev/cpu/0/msr
```

msr 都是 per-cpu 的设备，所以需要指定具体 cpu。 通过 **lseek 来定位 msr，通过 write/read 来读写**

通过这种方式来获取 cpu 性能是 bypass 内核，同样无法利用到 perf_event 子系统提供的一系列功能，比如关联某个 task， cgroup，也无法在有限的 pmu 个数中产生分时复用



需要配置event和unmask字段才会去采集对应的数据。





### 参考文献

[内核调试-perf introduction - 苏小北1024 - 博客园 (cnblogs.com)](https://www.cnblogs.com/muahao/p/8909211.html)

[performance - Good resources on how to program PEBS (Precise event based sampling) counters? - Stack Overflow](https://stackoverflow.com/questions/44218275/good-resources-on-how-to-program-pebs-precise-event-based-sampling-counters)

[PERF EVENT API篇-阿里云开发者社区 (aliyun.com)](https://developer.aliyun.com/article/590515)

[PERF EVENT 硬件篇-阿里云开发者社区 (aliyun.com)](https://developer.aliyun.com/article/590518)

[PERF EVENT 内核篇-CSDN博客](https://blog.csdn.net/weixin_33756418/article/details/89720185)

[PERF EVENT 硬件篇续 -- core/offcore/uncore-阿里云开发者社区 (aliyun.com)](https://developer.aliyun.com/article/590519)

Busybox可能在后续资源监控中会使用：

[Linux kernel + busybox自制Linux系统_飞腾 busybox-CSDN博客](https://blog.csdn.net/itas109/article/details/107737843)

[Busybox，这一篇就够了-CSDN博客](https://blog.csdn.net/qq_43193782/article/details/134079643)



![image-20240626145941076](C:\Users\user\AppData\Roaming\Typora\typora-user-images\image-20240626145941076.png)

[GitHub - sbu-fsl/kernel-ml: Machine Learning Framework for Operating Systems - Brings ML to Linux kernel](https://github.com/sbu-fsl/kernel-ml?tab=readme-ov-file#Example)
