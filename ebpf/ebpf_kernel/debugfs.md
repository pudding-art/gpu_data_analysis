# /sys/kernel/debug/

在 /sys/kernel/debug/ 目录下列出的这些子目录和文件是 debugfs 文件系统的一部分，它们提供了内核中各种调试和诊断信息的接口。每个子目录通常对应一个内核子系统或模块，用于导出该模块的调试信息。


1. accel：与加速器（如GPU或其他硬件加速器）相关的调试信息。通常用于查看和调整加速器的运行状态。
2. acpi：Advanced Configuration and Power Interface（高级配置与电源接口）相关的调试信息。用于检查和调试 ACPI 设备的配置和电源管理状态。
3. bdi：Block Device Interface（块设备接口）相关的调试信息。用于监控块设备的性能和状态。
4. block：块设备（如硬盘、SSD 等）的调试信息。用于查看块设备的 I/O 请求、调度器状态等。
5. bluetooth：蓝牙子系统的调试信息。用于监控蓝牙设备的连接状态和数据传输。
6. check_wx_pages：检查和调试内核中同时具有写和执行权限的页面。通常用于安全相关的调试。
7. clear_warn_once：用于清除内核中 WARN_ONCE 警告的调试工具。通过写入特定值可以清除警告计数。
8. clk：时钟管理相关的调试信息。用于查看和调整内核中时钟的配置和状态。
9. devfreq：设备频率管理相关的调试信息。用于动态调整设备的频率以优化性能和功耗。
10. device_component：设备组件管理相关的调试信息。用于监控和调试设备组件的状态。
11. dma_buf：DMA缓冲区相关的调试信息。用于查看和调试DMA缓冲区的使用情况。
12. dmaengine：DMA引擎相关的调试信息。用于监控和调试DMA引擎的运行状态。
13. dma_pools：DMA池相关的调试信息。用于查看和调试DMA池的分配和使用情况。
14. dri：Direct Rendering Infrastructure（直接渲染架构）相关的调试信息。用于调试图形设备的渲染状态。
15. dynamic_debug：动态调试接口。通过这个接口可以动态控制内核调试信息的输出，例如启用或禁用特定的调试消息。
16. energy_model：能量模型相关的调试信息。用于监控和调试内核的能量管理策略。
17. **extfrag：内存碎片化相关的调试信息。用于查看和调试内存碎片化的情况。**
18. **fault_around_bytes：用于调试内核中的页面错误处理。通过调整这个值可以控制内核在处理页面错误时的行为。**
19. gpio：GPIO（通用输入输出）相关的调试信息。用于查看和调试GPIO引脚的状态和配置。
20. hte：硬件跟踪扩展（Hardware Trace Extensions）相关的调试信息。用于调试硬件跟踪功能。
21. i2c：I2C总线相关的调试信息。用于查看和调试I2C设备的通信状态。
22. **interconnect：内核中互连设备的调试信息。用于监控和调试互连设备的带宽和性能。**
23. iosf_sb：**Intel On-Die System Fabric Sideband（Intel 芯片内部系统总线）相关的调试信息。用于调试Intel平台的内部通信。**
24. **kprobes：内核探针（kprobes）相关的调试信息。用于在内核代码中插入探针，动态捕获运行时信息。**
25. **lru_gen：内存页回收策略（LRU 生成器）相关的调试信息。用于监控和调试内存页的回收策略。**
26. **lru_gen_full：LRU生成器的完整调试信息。提供更详细的内存页回收策略信息。**
27. mce：Machine Check Exception（机器检查异常）相关的调试信息。用于监控和调试硬件错误检测。
28. pinctrl：引脚控制（Pin Control）相关的调试信息。用于查看和调试引脚的配置和状态。
29. pm_genpd：电源管理通用电源域（Power Management Generic Power Domain）相关的调试信息。用于监控和调试电源管理策略。
30. phy：物理层（PHY）设备的调试信息。用于查看和调试物理层设备的状态。
31. pwm：脉宽调制（PWM）相关的调试信息。用于查看和调试 PWM 设备的配置和状态。
32. **regmap：寄存器映射（Regmap）相关的调试信息。用于查看和调试寄存器映射的状态。**
33. **remoteproc：远程处理器（Remote Processor）相关的调试信息。用于调试和监控远程处理器的状态。**
34. regulator：电源管理调节器（Regulator）相关的调试信息。用于查看和调试电源管理调节器的状态。
35. **sched：调度器相关的调试信息。用于监控和调试内核调度器的行为。**
36. sleep_time：睡眠时间相关的调试信息。用于查看和调试设备的睡眠时间。
37. **split_huge_pages：分割大页面（Split Huge Pages）相关的调试信息。用于查看和调试大页面的分割策略。**
38. **stackdepot：栈沉积（Stack Depot）相关的调试信息。用于监控和调试内核栈的使用情况。**stack depot 是 Linux 内核中用于存储和管理堆栈跟踪（stack traces）的一种机制。它通过使用哈希表来避免重复存储相同的堆栈跟踪，从而节省内存。
39. suspend_stats：挂起统计（Suspend Statistics）相关的调试信息。
用于查看和调试系统挂起的统计信息。
40. **swiotlb：软件 I/O TLB（Software I/O Translation Lookaside Buffer）相关的调试信息。用于查看和调试软件 I/O TLB 的使用情况。**
41. **sync：同步相关的调试信息。用于查看和调试同步操作的状态。**
42. ttm：Translation Table Maps（翻译表映射）相关的调试信息。用于调试图形设备的内存管理。
43. **tracing：内核跟踪（Tracing）相关的调试信息。用于监控和调试内核事件的跟踪。**
44. usb：USB 子系统的调试信息。用于查看和调试 USB 设备的状态。
45. virtio-ports：Virtio 端口相关的调试信息。用于调试虚拟设备的端口状态。
46. **vmmemctl：虚拟内存控制相关的调试信息。用于查看和调试虚拟内存的配置和状态。**
47. wakeup_sources：唤醒源相关的调试信息。用于查看和调试系统唤醒的源。
48. x86：x86 架构相关的调试信息。用于调试 x86 平台的特定功能。
49. ras：可靠性、可用性和可维护性（Reliability, Availability, and Serviceability）相关的调试信息。用于监控和调试硬件错误检测和处理。
50. **split_huge_pages：分割大页面相关的调试信息。用于查看和调试大页面的分割策略。**


![tracing_kprobes](image-4.png)

## /sys/kernel/debug/tracing

/sys/kernel/debug/tracing 是 Linux 内核中用于内核跟踪（kernel tracing）的接口，提供了丰富的调试和性能分析功能。这些文件和目录允许用户动态地启用、配置和查看内核跟踪信息。

1. available_events:列出内核中所有可用的跟踪事件。用于查看可以启用的事件类型。
2. available_filter_functions:列出可以用于过滤的函数列表。用于设置函数过滤器，限制跟踪的范围。
3. available_filter_functions_addrs:列出可以用于过滤的函数的地址。与 available_filter_functions 类似，但提供的是函数的内存地址。
4. available_tracers:列出内核中可用的跟踪器（tracers）。用于查看可以启用的跟踪器类型。
5. buffer_percent:显示当前跟踪缓冲区的使用百分比。用于监控缓冲区的使用情况。
6. buffer_size_kb:设置或显示跟踪缓冲区的大小（以 KB 为单位）。用于调整缓冲区大小以适应不同的跟踪需求。
7. buffer_subbuf_size_kb:设置或显示每个 CPU 的子缓冲区大小（以 KB 为单位）。用于优化缓冲区的分配。
8. buffer_total_size_kb:显示跟踪缓冲区的总大小（以 KB 为单位）。用于查看当前缓冲区的总容量。
9. current_tracer:显示当前启用的跟踪器。用于查看或设置当前使用的跟踪器。
10. dynamic_events:用于动态创建和管理自定义事件。通过写入特定格式的字符串来创建事件。
11. dyn_ftrace_total_info:显示动态函数跟踪（ftrace）的统计信息。用于查看动态跟踪的函数数量和状态。
12. enabled_functions:列出当前启用的函数跟踪。用于查看哪些函数正在被跟踪。
13. error_log:记录跟踪子系统的错误日志。用于调试和诊断跟踪问题。
14. events:包含所有可用事件的目录。每个事件都有自己的子目录，用于启用或禁用事件。
15. free_buffer:用于释放跟踪缓冲区。通过写入特定值可以清空缓冲区。
16. function_profile_enabled:控制是否启用函数性能分析。用于启用或禁用函数级别的性能分析。
17. hwlat_detector:用于检测硬件延迟。提供硬件延迟检测的配置和结果。
18. instances:包含用户创建的跟踪实例的目录。用于管理多个独立的跟踪会话。
19. kprobe_events:用于管理 kprobe 事件。通过写入特定格式的字符串来创建或删除 kprobe 事件。
20. kprobe_profile:提供 kprobe 事件的性能分析数据。用于查看 kprobe 事件的统计信息。
21. max_graph_depth:设置函数图跟踪的最大深度。用于限制跟踪的函数调用深度。
22. osnoise:用于操作系统噪声（osnoise）的跟踪和分析。用于监控和分析内核噪声。
23. options:包含跟踪子系统的各种选项。每个选项都有自己的文件，用于启用或禁用特定功能。
24. osnoise:用于操作系统噪声（osnoise）的跟踪和分析。用于监控和分析内核噪声。
25. per_cpu:包含每个 CPU 的跟踪数据。每个 CPU 有自己的子目录，用于查看特定 CPU 的跟踪信息。
26. printk_formats:列出内核日志（printk）的格式字符串。用于调试和查看日志格式。
27. README:提供跟踪子系统的使用说明。包含基本的使用指南和示例。
28. rv:用于记录和查看内核的运行时验证（Runtime Verification）信息。用于调试和验证内核行为。
29. saved_cmdlines:保存进程的命令行参数。用于查看进程的启动参数。
30. saved_cmdlines_size:显示保存的命令行参数的大小。用于查看保存的命令行参数的容量。
31. saved_tgids:保存线程组 ID（TGID）。用于查看和管理线程组 ID。
32. set_event:用于启用或禁用特定事件。通过写入事件名称可以启用或禁用事件。
33. set_event_notrace_pid:设置不跟踪的进程 ID。用于排除特定进程的跟踪。
34. set_event_pid:设置要跟踪的进程 ID。用于限制跟踪的进程范围。
35. set_ftrace_filter
设置函数跟踪的过滤器。
用于限制跟踪的函数范围。
36. set_ftrace_notrace
设置不跟踪的函数。
用于排除特定函数的跟踪。
37. set_ftrace_notrace_pid
设置不跟踪的进程 ID。
用于排除特定进程的跟踪。
38. set_ftrace_pid
设置要跟踪的进程 ID。
用于限制跟踪的进程范围。
39. set_graph_function
设置要跟踪的函数图。
用于启用函数图跟踪。
40. set_graph_notrace
设置不跟踪的函数图。
用于排除特定函数图的跟踪。
41. snapshot
用于创建跟踪数据的快照。
通过写入特定值可以捕获当前的跟踪数据。
42. stack_max_size
设置堆栈跟踪的最大大小。
用于限制堆栈跟踪的存储大小。
43. stack_trace
显示当前的堆栈跟踪。
用于查看当前的调用堆栈。
44. stack_trace_filter
设置堆栈跟踪的过滤器。
用于限制堆栈跟踪的范围。
45. synthetic_events
用于创建和管理合成事件。
通过写入特定格式的字符串来创建自定义事件。
46. touched_functions
显示被跟踪的函数列表。
用于查看哪些函数被跟踪过。
47. trace
显示当前的跟踪数据。
用于查看实时的跟踪输出。
48. trace_clock
设置或显示跟踪的时间戳时钟源。
用于选择时间戳的来源（如 local、global 等）。
49. trace_marker
用于向跟踪缓冲区中写入标记。
通过写入字符串可以在跟踪数据中插入自定义标记。
50. trace_marker_raw
用于向跟踪缓冲区中写入原始标记。
与 trace_marker 类似，但用于写入原始数据。
51. trace_options
包含跟踪选项的目录。
每个选项都有自己的文件，用于启用或禁用特定功能。
52. trace_pipe
提供实时的跟踪数据流。
用于查看实时的跟踪输出，适合管道输出到其他工具。
53. trace_stat
显示跟踪统计信息。
用于查看跟踪的性能和状态。
54. tracing_cpumask
设置跟踪的 CPU 范围。
用于限制跟踪的 CPU。
55. tracing_max_latency
显示或设置最大跟踪延迟。
用于记录和设置内核的最大延迟。
56. tracing_on
控制跟踪的开关。
通过写入 1 或 0 可以启用或禁用跟踪。
57. tracing_thresh
设置跟踪的延迟阈值。
用于过滤低于阈值的延迟事件。
58. timestamp_mode
设置时间戳的模式。
用于选择时间戳的显示方式。
59. uprobe_events
用于管理 uprobe 事件。
通过写入特定格式的字符串来创建或删除 uprobe 事件。
60. uprobe_profile
提供 uprobe 事件的性能分析数据。
用于查看 uprobe 事件的统计信息。
61. user_events_data
用于管理用户定义的事件数据。
用于存储和查看用户定义的事件信息。
62. user_events_status
显示用户定义事件的状态。
用于查看用户定义事件的启用或禁用状态。
## /sys/kernel/debug/kprobes


/sys/kernel/debug/kprobes 目录下的文件提供了对内核探针（Kprobes）的调试和管理接口。

1. blacklist
列出内核中不能被 Kprobes 探测的函数。
这些函数可能是由于递归陷阱（如双重错误）或嵌套探针处理程序可能永远不会被调用而被加入黑名单。
通过使用 NOKPROBE_SYMBOL() 宏，可以将函数添加到黑名单中。Kprobes 会检查给定的探测地址，如果该地址在黑名单中，则会拒绝注册该地址。
2. enabled
用于全局且强制地打开或关闭已注册的 Kprobes。
默认情况下，所有 Kprobes 都是启用的。通过向此文件写入 0，可以解除武装所有已注册的探针，直到向此文件写入 1 为止。
注意，这个旋钮只是解除和武装所有 Kprobes，并不会更改每个探针的禁用状态。这意味着，如果您通过此旋钮打开所有 Kprobes，禁用的 Kprobes（标记为 [DISABLED]）将不会被启用。
3. list
列出系统上所有已注册的探针。
每行的格式如下：
第一列：探针插入的内核地址。
第二列：探针的类型（k 表示 kprobe，r 表示 kretprobe）。
第三列：探针的符号+偏移量。
如果被探测的函数属于一个模块，也会指定模块名称。
后面的列显示探针状态：
[GONE]：探针位于不再有效的虚拟地址上（模块初始化部分、与已卸载模块对应的模块虚拟地址）。
[DISABLED]：探针被暂时禁用。
[OPTIMIZED]：探针已优化。
[FTRACE]：探针是基于 ftrace 的

查看已注册的 Kprobes:
```shell
cat /sys/kernel/debug/kprobes/list
```
启用或禁用所有 Kprobes：
```shell
echo 1 > /sys/kernel/debug/kprobes/enabled  # 启用
echo 0 > /sys/kernel/debug/kprobes/enabled  # 禁用
```
查看黑名单中的函数:
```shell
cat /sys/kernel/debug/kprobes/blacklist
```