以下是一个阅读该源码的建议步骤：

### 1. 先看顶层目录和文件

  * **examples 文件夹** ：
    * 这里的 demo notebooks 是很好的学习入口。它们通常会包含如何使用 HTA 工具进行各种分析的示例代码和说明。通过阅读这些示例，你可以快速了解 HTA 能够完成哪些功能，以及这些功能的大致调用方式。比如，你可以看到如何加载一个追踪文件，然后使用不同的分析器来进行性能分析等操作。

  * **hta 包下的 trace_analysis.py 和 trace_diff.py** ：
    * 这两个文件是 TraceAnalysis API 和 TraceDiff API 的入口点。理解它们对于掌握 HTA 的核心使用方法至关重要。你可以查看它们是如何定义类和函数，以及如何接收参数、调用内部的 analyzers 等模块来完成分析任务的。trace_analysis.py 应该包含了启动各种性能分析流程的关键逻辑，而 trace_diff.py 则是用于比较不同追踪文件差异的核心文件，它们可以让你对 HTA 的主要功能调用流程有一个初步的认识。

### 2. 钻研 hta 包内部的子模块

  * **analyzers 模块** ：
    * 这是 HTA 的核心逻辑所在。它包含了各种不同的分析器，每个分析器对应一种特定的分析功能，比如之前提到的 temporal breakdown、kernel breakdown 等等。你可以逐个查看这些分析器的类定义，了解它们的属性和方法。研究它们是如何处理追踪数据，提取有用信息并进行分析的。例如，查看一个分析器是如何从追踪文件中读取时间戳信息来计算不同任务的时间分布的，或者如何解析 GPU 内核的调用信息来生成内核性能分析结果等。

  * **common 模块** ：
    * 这个模块包含多个分析器共用的代码。查看其中的内容可以帮助你了解不同分析功能之间共享的工具函数、数据结构或者通用的处理逻辑。比如，可能有一些用于解析追踪文件格式的通用函数，或者一些计算统计指标的工具类方法，这些在多个分析器中都会被调用。

  * **configs 模块** ：
    * 这里的配置文件定义了 HTA 的各种可配置参数，如日志记录级别等。了解这些配置文件的格式和内容，可以帮助你掌握如何调整 HTA 的运行时行为。例如，你可能需要修改日志级别来进行调试，或者调整一些分析相关的参数来适应特定的分析需求。

  * **utils 模块** ：
    * 工具模块通常包含一些辅助性的函数和类，它们可能用于文件操作、数据转换、可视化等多个方面。研究这个模块可以使你更全面地了解 HTA 的实现细节，比如它是如何读写追踪文件的，如何将分析结果转换为易于展示的格式，或者如何生成图表等可视化内容来呈现分析结果。

### 3. 查看 scripts 文件夹

  * 这里的通用工具脚本可能包含一些用于处理追踪文件的辅助工具。例如，可能有脚本可以用来合并多个追踪文件、对追踪文件进行预处理或者提取特定信息等。阅读这些脚本可以帮助你了解如何在更大的工作流程中利用 HTA 工具，以及如何对追踪数据进行一些基础的操作。

### 4. 最后看 tests 文件夹

  * 单元测试文件可以让你了解各个模块的预期行为。通过阅读测试用例，你可以看到每个函数或类在不同输入情况下的预期输出和行为，这有助于你更深入地理解源码的正确性和功能边界。同时，测试代码也可以作为示例，展示如何正确地调用 HTA 的各个组件来进行测试和验证。

在整个阅读源码的过程中，要注意结合实际的调试和运行。可以尝试修改一些简单的代码，观察程序的行为变化；也可以在关键函数中添加调试信息输出，来跟踪代码的执行流程和数据的处理过程。这样可以加深你对源码的理解，并且能够更快地掌握 HTA 工具的使用和开发方法。

- [] 如何设计，如何知道需要探测这些数据？


### Temporal breakdown
https://github.com/facebookresearch/HolisticTraceAnalysis/blob/main/examples/trace_analysis_demo.ipynb

Temporal breakdown将GPU时间划分为三部分：
1. Idle time：GPU处于空闲状态，没有执行任何任务
2. Compute time：GPU忙于执行计算任务，如同步计算内核
3. Non-compute time：非计算时间，GPU忙于执行分计算任务，如数据传输等通信任务，以及内存操作
```python
# Temporal breakdown
temporal_breakdown_df = analyzer.get_temporal_breakdown()
```
通过Temporal breakdown可以了解GPU的时间分配情况，进而优化程序以减少空闲时间，提高计算和非计算任务的效率。

- [ ] 代码中这三种时间爱你是如何计算的,输出结果包括了idle_time, compute_time, non-compute_time和kernel_time，以及后面时间对应的百分比, 输出数据的多样性


### Kernel breakdown
Kernel breakdown是一个用于分析GPU内核执行时间的功能，它提供了以下信息：
1. 不同内核类型的时间分布(所有rank的整体角度)
    - 计算内核：执行计算任务的内核，执行矩阵乘法和类似数值计算，负责模型执行所需的所有数字运算，如同步计算、矩阵乘法等
    - 通信内核：涉及数据传输任务的内核，在分布式训练作业中交换和同步不同GPU设备之间的数据，如GPU之间的数据传输、集合通信操作等。其所有kernel function都带有前缀`nccl`,比如`nccl_allgather`,`nccl_reducescatter`,`nccl_allreduce`等
    - 内存内核：涉及内存操作的内核，负责管理GPU设备上的内存分配与释放，以及主机和GPU熵的内存空间之间的数据移动，如内存分配、内存拷贝等，内存kernel fuction主要包括 `memcpy_H2D`  ,`memcpu_D2H`,`memcpy_D2D`, `memset`等
2. 每个Rank上最耗时的内核（顶级耗时内核，每个rank内部时间分布）
    - 对于每个rank，找出每种kernel类型中最耗时的具体kernel，有助于识别性能瓶颈，比如某个rank上的comm kernel可能特别耗时，表明可能存在通信瓶颈
    - [ ] 这里是将每个rank中的每种类型kernel的最耗时的都列出来，也就是1个rank->comp,comm,mem对应三个kernel
3. 最耗时内核的平均时间分布(不同rank之间相互比较)
    - 对于每个rank上最耗时的内核，计算其平均执行时间的分布。这可以反应不同rank之间执行时间的差异，可能表明负载不均衡或其他问题。

```python
# Kernel breakdown
kernel_breakdown_df = analyzer.get_gpu_kernel_breakdown(visualize=False[True], # 输出是pie/bar chart,还是dataFrame
num_kernels = 10, # 显示的内核数量，优先级高于duration_ratio
duration_ratio = 0.9,  # 分析总执行时间占总时间90%的内核
include_memory_kernels = True[False] # 是否包含对memory kernels相关内容的分析，False：分析仅包括通信和计算内核，计算方式为：(计算和通信重叠时间) / (通信时间 + 计算时间)。)
```
- 饼图（内核类型分布）：展示了计算、通信和内存内核所占的总时间百分比。
- 饼图（最耗时内核）：对于每个 rank，展示了每种内核类型中最耗时的内核所占的时间百分比。
- 柱状图（内核执行时间）：对于每个 rank，展示了每种内核类型中最耗时的内核的平均执行时间，并带有误差线，表示每个内核在不同 rank 上的最小和最大执行时间。


<mark>**[例子]**</mark>假设我们有一个分布式深度学习训练任务，使用了8个GPU进程（Rank 0到 Rank 7）。通过Kernel Breakdown功能，我们可能得到以下结果：
- 时间分布：通信内核在所有Rank上总共占用了60%的时间，计算内核占用了30%，内存内核占用了10%。这表明通信可能是一个主要的性能瓶颈。
- 顶级耗时内核（按类型）：
    - 在计算类内核中，`aten::linear`（线性层计算）在每个Rank上都是最耗时的计算内核.
    - 在通信类内核中，`nccl:all_reduce`（一种集体通信操作）在每个Rank上都是最耗时的通信内核,或者在rank1上`nccl:all_reduce`最耗时，但是rank2上`nccl:allgather`耗时最长。
    - 在内存类内核中，`cudaMemcpy`（内存拷贝操作）在每个Rank上都是最耗时的内存内核。
- 平均时间分布（指的是同一种kernel在不同rank上的分布情况）：
    - 对于`aten::linear`内核，其在Rank 0到Rank 7上的平均执行时间分别为 100ms、110ms、95ms、105ms、102ms、98ms、107ms、103ms。这显示出**不同Rank上该内核的执行时间存在一定的波动，可能需要进一步分析原因，比如数据分布、计算负载不均等**。
    - 对于`nccl:all_reduce`内核，平均执行时间在各个Rank上相对较为一致，但也可能发现某些Rank上由于网络延迟等因素导致该内核执行时间较长。


通过以上信息，开发者可以针对性地进行优化，比如优化通信策略、调整计算内核的实现、平衡内存操作负载等，从而提升整个分布式系统的性能。

- [] 为什么将内存kernel单独列出来？


### Kernel Attribtion to Annotations

“Kernel Attribution to Annotations”是PyTorch提供的一个功能，允许开发者将自定义的注释（annotations）与GPU内核相关联。这些注释可以为内核提供上下文信息，帮助开发者了解**每个内核属于哪个模块或组件**，可以更清晰地了解每个模块的性能贡献，从而实现更细致的性能分析和优化。

- 用户标记注释：开发者在代码中使用`torch.profiler.record_function`插入自定义注释，标记代码中的特定区域或操作。
- 内核与注释关联：PyTorch的分析工具将这些注释与GPU内核相关联，使每个内核的执行时间能够被归因到特定的模块或组件。
- 数据框返回：功能返回一个包含所有GPU内核的完整数据框，其中每个内核都与相应的用户注释相关联。用户可以在数据框上进行聚合操作，例如按模块或组件汇总内核的执行时间。

```python
analyzer.get_gpu_kernels_with_user_annotations(
    rank: int, # 获取特定进程的内核数据
    expand_names: bool = True, # 是否展开为完整名称，True则增加两列"s_name":内核的完整名称,"s_user_annotation":用户注释的完整名称。
    shortern_names: bool = True, # 是否缩短较长的CUDA内核名称
) -> Optional[pandas.core.frame.DataFrame]

gpu_kernels_df = analyzer_user_anno.get_gpu_kernels_with_user_annotations(rank=0, expand_names=True, shortern_names=False)

gpu_kernels_df[["s_name", "s_cat", "s_user_annotation", "stream", "ts", "dur"]] # 预先定义好的字段
#[内核名称, 内核类别, 用户提供的注释, 内核所属的CUDA stream, 时间戳, 内核的执行时间]
```

- [ ] 该函数无可视化功能
- [ ] 没有annotation的地方输出的部分写啥

当一个GPU内核与多个用户注释关联时，目前的实现会将其归因到堆栈中最底层的注释。这种行为可能是基于一种假设，即最底层的注释最能代表内核执行时的具体上下文。计划在未来支持一个堆栈列，这将允许用户查看内核关联的整个注释堆栈，而不仅仅是最低层的注释。这将为用户提供最丰富的信息，帮助他们更全面地理解内核执行的上下文。

注释堆栈列是指在性能分析工具中，记录每个内核执行时与之关联的所有用户注释的完整堆栈信息。例如，一个内核可能在一个函数注释内执行，而该函数注释又在一个模块注释内，模块注释又在一个阶段注释内。最底层的注释通常是在代码中离内核启动点最近的注释。因此，它更能准确反映内核的具体执行上下文。


- [ ] 缺少完整的堆栈列annotation的注释
```python
with torch.profiler.record_function("Training_Phase"):
    with torch.profiler.record_function("Model_Forward"):
        output = model(input)
```
以上对应的堆栈列可以增加一个annotation_stack字段而不只是annotation，显示全路径注释：
| s_name | s_cat | annotation_stack | 
| --- | --- | --- | 
| kernel1 | kernel | ['Training_Phase', 'Model_Forward'] | 
| kernel2 | kernel | ['Training_Phase', 'Model_Forward'] | 


当前要求用户必须指定一个rank才能获取该rank的GPU内核数据，因为在分布式计算环境中，每个rank是一个独立的进程，可能执行不同的代码路径并生成不同的内核调用。通过指定rank，可以确保返回的数据是特定于该进程的。由于每个rank的内核数据可能是独立的，将它们分开处理可以避免数据混淆，并使用户能够更精确地分析每个进程的性能。

```python
import torch
import torch.profiler
from hta.trace_analysis import TraceAnalysis

# 定义一个简单的线性层和激活函数
linear_layer = torch.nn.Linear(10, 10)
activation = torch.nn.ReLU()
input = torch.randn(10, 10)

# 使用 PyTorch Profiler 进行性能分析
with torch.profiler.profile(
    activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA],
    record_shapes=True,
    profile_memory=True,
) as prof:
    # 标记模块的开始
    with torch.profiler.record_function("my_custom_module"):
        # 执行线性层计算
        output = linear_layer(input)
        # 执行激活函数计算
        output = activation(output)

# 查看分析结果
print(prof.key_averages().table(sort_by="cuda_time_total"))

# 获取内核与注释关联的数据框
kernel_annotation_df = analyzer.get_gpu_kernels_with_user_annotations(rank=0, expand_names=True, shortern_names=True)

# 对内核执行时间按注释进行聚合
aggregated_df = kernel_annotation_df.groupby('user_annotation')['time'].sum().reset_index()

# 显示结果
print(aggregated_df)
```


### Communication Computation Overlap
Communication Computation Overlap 是一个重要的性能指标，用于衡量在分布式计算中通信和计算重叠的程度。这个指标可以帮助开发者了解通信和计算任务是否高效地并行执行，从而优化程序性能。
Communication Computation Overlap 的计算公式为：

​![comp](image.png)
 
- Time Spent Computing While Communicating：在通信操作（如数据传输）进行的同时，GPU 或 CPU 仍在执行计算任务的时间。
- Total Time Spent Communicating：通信操作的总时间。

需要知道时间戳和duration。

```python
# Communication computation overlap
comm_comp_overlap_df = analyzer.get_comm_comp_overlap()
```
### Idle time breakdown(对第一个功能的进一步细分)
对GPU的idle time进行进一步分解，分为Host等待时间、内核等待时间和其他等待时间。可以据此定位导致GPU空闲的具体原因，从而采取针对性的优化措施。

- Host wait time：由于CPU线程没有向GPU队列中添加足够的内核任务，导致GPU流（stream）处于空闲状态的时间。通常是因为CPU的准备工作（如数据预处理、任务调度等）耗时较长，无法及时为GPU提供足够的任务。可以优化CPU代码，减少数据预处理时间，或者调整任务调度逻辑，使CPU能更高效地为GPU提供任务。也可以考虑增加 GPU的并行任务，减少GPU等待CPU的时间。
- Kernel wait time: 内核之间短暂的空闲时间，通常是因为启动多个小型内核的开销导致的。当多个小内核依次执行时，内核启动和切换会有一定的延迟，这些延迟累积起来就形成了内核等待时间。如果内核之间的间隔小于设定的阈值（如 30 毫秒），则将这些间隔归类为内核等待时间。尽量减少小型内核的使用频率，将多个小型内核合并为一个较大的内核，以减少内核启动和切换的开销。或者优化内核启动逻辑，降低内核启动的延迟。
- Other wait time:由于未知原因导致的GPU空闲时间。可能是因为计算内核在等待CUDA事件，或者其他未明确识别的原因。需要进一步分析和调试代码，找出导致GPU空闲的具体原因。可以使用更详细的性能分析工具或调试器，检查CUDA事件的同步逻辑，确保内核之间能够高效协作，减少不必要的等待时间。



- idle_tile_df = rank stream idle_category idle_time idle_time_ratio

- interval_stats_df = idle_category rank stream count(所有的idle intervals数量) mean(idle time/count) std min 25% 50% 75% max

```python
# Idle time breakdown
idle_time_df = analyzer.get_idle_time_breakdown()
```


### Augmented Counters(Queue Length and Memory Bandwidth)
向追踪数据中添加额外的计数器和时间序列信息，以便更全面地分析GPU的性能。
- 队列长度 (Queue Length)：表示在某个CUDA流中尚未完成的CUDA操作的数量。
- 内存带宽 (Memory copy bandwidth)：显示在不同内存之间（如主机到设备、设备到主机、设备到设备）的数据传输速率的时间序列。



```python
analyzer.generate_trace_with_counters(
    time_series: Optional[hta.trace_analysis.TimeSeriesTypes] = None, #指定要添加的时间序列类型。可选值为 TimeSeriesTypes.QUEUE_LENGTH（队列长度）和 TimeSeriesTypes.MEMCPY_BANDWIDTH（内存带宽）。默认情况下，两者都会被添加。
    ranks: Optional[List[int]] = None, # 指定要生成计数器的 rank 列表。默认为 [0]。
    output_suffix: str = '_with_counters', # 指定生成的追踪文件的后缀名。默认为 _with_counters.json.gz。
) -> None #该方法不返回值，而是生成新的追踪文件。



# Queue length summary
# get_queue_length_summary() 方法用于计算和返回每个 CUDA 流的队列长度统计信息，这些信息汇总在称为数据框的表格结构中，每行代表一个特定 CUDA 流的统计摘要。
ql_summary = analyzer.get_queue_length_summary(ranks = [1])

# Raw time series
queue_length_dict = analyzer.get_queue_length_time_series(ranks: Optional[List[int]] = None) -> Dict[int, pandas.core.frame.DataFrame]

# Time spent blocked on a kernel launch queue.
analyzer.get_time_spent_blocked_on_full_queue(
    queue_length_dict: Dict[int, pandas.core.frame.DataFrame], # queue_length_dict 是一个字典，键是 rank（进程编号），值是 pandas.DataFrame 数据框。每个数据框包含对应 rank 的 CUDA 流队列长度的时间序列数据。queue_length_dict 是通过调用 analyzer.get_queue_length_time_series() 方法得到的，它包含了每个 rank 的 CUDA 流队列长度的时间序列数据。
    max_queue_length: int = 1024, # 表示内核启动队列的最大长度。max_queue_length 是一个可调参数，默认值可能因工具或框架而异，但通常需要根据具体的 GPU 和应用场景进行设置。
) -> Optional[pandas.core.frame.DataFrame]
```

该API会为指定的rank生成新的追踪文件，并在文件名后添加指定的后缀（默认为 _with_counters.json.gz）。新文件中包含了额外的时间序列数据，用于更深入的性能分析。

为什么队列长度和内存带宽在这里是时序类型？

1. 队列长度反映的是在某一时刻，CUDA 流中等待执行的操作数量。这个数值会随着内核的启动和完成而动态变化。只有通过记录不同时刻的队列长度，才能了解 GPU 的负载情况和任务调度的效率。例如，队列长度的增加可能表示任务提交速度超过了 GPU 的执行速度，或者某些内核执行时间过长，导致任务积压。
2. 内存带宽衡量的是在某一时间段内，数据在不同内存之间传输的速率。这个数值也会随时间变化，因为不同的操作会以不同的速率访问内存。通过记录不同时刻的内存带宽，可以了解内存传输的效率和瓶颈。例如，内存带宽的降低可能表示数据传输操作出现了问题，或者某些操作对内存的访问模式不够优化。

```python
# Memory bandwidth time series
memory_bw_series = analyzer.get_memory_bw_time_series()

# Memory bandwidth summary
memory_bw_summary = analyzer.get_memory_bw_summary()

# Queue length time series
ql_series = analyzer.get_queue_length_time_series()

```


当 CPU 向 GPU 提交内核时，它使用一个有限大小的队列。如果这个队列被填满，CPU 就不得不等待（阻塞），直到 GPU 能够启动更多的内核。这种情况可能发生在 GPU 正忙于其他任务或者内核被快速连续提交时。

函数 get_time_spent_blocked_on_full_queue() 用于确定 CPU 因队列满而等待 GPU 启动内核所花费的时间。它使用 get_queue_length_time_series() 方法返回的队列长度时间序列数据，来判断队列何时处于最大长度。

- `duration_at_max_queue_length`：队列处于最大长度的总时间（以纳秒为单位）。
- `relative_duration_at_max_queue_length`：相对于追踪总时长的 duration_at_max_queue_length。它表明阻塞时间在整体执行时间中的占比。

```python
blocked_time_df = analyzer.get_time_spent_blocked_on_full_queue(ranks=[0])
print(blocked_time_df)
```

### CUDA Kernel Launch Statistics
在GPU上启动的内核和在CPU上进行的调度操作是一一对应的。每个GPU内核启动事件都有一个对应的CPU调度事件，两者通过“相关ID”（correlation id）关联起来。

```python
# CUDA kernel launch statistics
cuda_launch_kernel_stats = analyzer.get_cuda_kernel_launch_stats()
```

这个功能主要用于计算以下几个关键时间指标：
- CPU 操作的持续时间：即 CPU 上调度事件的执行时间。
- GPU 内核的持续时间：即 GPU 上内核的执行时间。
- 启动延迟：即从 CPU 操作结束到 GPU 内核开始执行之间的时间差。这个指标反映了内核启动的效率。

| correlation | cpu_duration | gpu_duration | launch_delay | 
| --- | --- | --- | --- | 
| 278204 | 15 | 37 | 31 | 
| 278209 | 12 | 40 | 26 | 
| 278239 | 12 | 31 | 25 | 
| 278244 | 11 | 53 | 24 | 
| 278249 | 11 | 3 | 25 | 
| ... | ... | ... | ... | 
| 335216 | 13 | 103 | 24418 | 
| 335221 | 10 | 50 | 24471 | 
| 335229 | 12 | 55 | 24451 | 
| 335252 | 16 | 3045 | 21331 | 
| 335300 | 17 | 476 | 24022 | 

- correlation：相关ID，用于关联CPU调度事件和GPU内核启动事件。
- cpu_duration：CPU操作的持续时间（单位：毫秒）。
- gpu_duration：GPU内核的持续时间（单位：毫秒）。
- launch_delay：启动延迟，即从CPU操作结束到GPU内核开始执行的时间差（单位：毫秒）。

前几个内核的启动延迟在24到31毫秒之间，属于正常范围。
后几个内核的启动延迟显著增加，达到了24418、24471等，这表明这些内核的启动存在严重延迟。

通过这些指标，开发者可以了解内核执行的效率以及 CPU 和 GPU 之间的协调情况。




### Most Frequent CUDA Kernel Sequences
“Most Frequent CUDA Kernel Sequences” 功能的作用是识别在指定操作中启动的最常见的 CUDA 内核序列，帮助开发者发现可以优化的内核调用模式。当执行深度学习模型或其他 GPU 加速应用程序时，某些 CUDA 内核序列可能会频繁出现。识别这些频繁的内核序列有助于优化代码，例如通过内核融合减少内核启动次数和数据传输开销。




```python
frequent_cuda_kernels = analyzer.get_frequent_cuda_kernel_sequences(
    operator_name="aten::linear",  # 指定操作符名称
    output_dir="/tmp/",            # 指定生成的追踪文件的输出目录
    min_pattern_len=3,            # 指定最小内核序列长度
    rank=0,                       # 指定要分析的 rank
    top_k=5,                      # 指定要返回的最频繁序列的数量
    visualize=False               # 指定是否生成可视化结果
)

# Frequent CUDA kernel patterns
frequent_patterns_df = analyzer.get_frequent_cuda_kernel_patterns(operator_name="aten::linear", output_dir="/new/trace/path")


# print(frequent_cuda_kernels)
```

分析工具会识别在指定操作中启动的 CUDA 内核序列。该功能生成一个新的追踪文件，将识别出的最常见的 k 个内核模式叠加在原始追踪文件上。通过在新追踪文件中搜索“Patterns”关键词，相关 CPU 和 GPU 操作会被高亮显示，提示开发者关注这些位置以寻找内核融合或其他优化机会。"Patterns" 指的是特定的 CUDA 内核调用序列或组合。这些模式代表了在代码执行过程中频繁出现的内核调用系列。

## HTA环境配置

环境配置如下：
```python
python3 -m venv ~/hta_env
sudo apt install python3.12-venv
source ~/hta-venv/bin/activate

cd HolisticTraceAnalysis/
pip install -r requirements.txt
pip install -e .
```



```python
import inspect
from hta.trace_analysis import TraceAnalysis


hta_dir = "/home/hwt/HolisticTraceAnalysis"
trace_dir = hta_dir + "/tests/data/vision_transformer"

analyzer = TraceAnalysis(trace_dir = trace_dir)

# print(type(analyzer))

time_spent_df = analyzer.get_temporal_breakdown(visualize=False)

print(inspect.getsource(analyzer.get_temporal_breakdown))

kernel_type_metrics_df, kernel_metrics_df = analyzer.get_gpu_kernel_breakdown(visualize = False, 
                                                                              duration_ratio = 0.8,
                                                                              num_kernels = 5,
                                                                              include_memory_kernels = True)


print(kernel_type_metrics_df)
print("################")
print(kernel_metrics_df)
```

```shell
(hta_venv) hwt@hwt-VMware-Virtual-Platform:~/HolisticTraceAnalysis/workspace$ python3 test.py 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-1.json.gz time = 1.55 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-0.json.gz time = 1.57 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-0.json.gz backend=ParserBackend.JSON in 5.49 seconds; current PID:23857
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-1.json.gz backend=ParserBackend.JSON in 5.53 seconds; current PID:23858
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-0.json.gz in 6.71 seconds; current PID:23857
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-1.json.gz in 6.74 seconds; current PID:23858
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-2.json.gz time = 1.62 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-3.json.gz time = 1.61 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-2.json.gz backend=ParserBackend.JSON in 5.65 seconds; current PID:23857
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-3.json.gz backend=ParserBackend.JSON in 5.58 seconds; current PID:23858
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-2.json.gz in 6.56 seconds; current PID:23857
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-3.json.gz in 6.65 seconds; current PID:23858
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-4.json.gz time = 1.74 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-5.json.gz time = 1.64 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-4.json.gz backend=ParserBackend.JSON in 5.71 seconds; current PID:23857
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-5.json.gz backend=ParserBackend.JSON in 5.66 seconds; current PID:23858
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-4.json.gz in 6.76 seconds; current PID:23857
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-5.json.gz in 6.74 seconds; current PID:23858
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-6.json.gz time = 1.82 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-7.json.gz time = 1.69 seconds 
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-6.json.gz backend=ParserBackend.JSON in 5.62 seconds; current PID:23857
Parsed /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-7.json.gz backend=ParserBackend.JSON in 5.32 seconds; current PID:23858
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-6.json.gz in 6.53 seconds; current PID:23857
Overall parsing of /home/hwt/HolisticTraceAnalysis/tests/data/vision_transformer/rank-7.json.gz in 6.43 seconds; current PID:23858
leaving parse_multiple_ranks duration=31.96 seconds
leaving parse_traces duration=31.96 seconds
   rank  idle_time(us)  compute_time(us)  non_compute_time(us)  kernel_time(us)  idle_time_pctg  compute_time_pctg  non_compute_time_pctg
0     0       552069.0          596651.0              884850.0        2033570.0           27.15              29.34                  43.51
1     1       431771.0          596759.0             1004227.0        2032757.0           21.24              29.36                  49.40
2     2       312107.0          596886.0             1124788.0        2033781.0           15.35              29.35                  55.31
3     3       274646.0          604137.0             1154491.0        2033274.0           13.51              29.71                  56.78
4     4       418833.0          598040.0             1021824.0        2038697.0           20.54              29.33                  50.12
5     5       318972.0          601581.0             1112561.0        2033114.0           15.69              29.59                  54.72
6     6       388040.0          598029.0             1047787.0        2033856.0           19.08              29.40                  51.52
7     7       454830.0          599358.0              979022.0        2033210.0           22.37              29.48                  48.15
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
/home/hwt/HolisticTraceAnalysis/hta/analyzers/breakdown_analysis.py:517: FutureWarning: Downcasting behavior in `replace` is deprecated and will be removed in a future version. To retain the old behavior, explicitly call `result.infer_objects(copy=False)`. To opt-in to the future behavior, set `pd.set_option('future.no_silent_downcasting', True)`
  kernel_t_df.melt(var_name="status", value_name="time").replace(
                             kernel_type      sum  percentage
0                          COMMUNICATION  8040285        61.3
1                            COMPUTATION  2671248        20.4
2  COMPUTATION overlapping COMMUNICATION  2119629        16.2
3                                 MEMORY   273227         2.1
4       COMMUNICATION overlapping MEMORY    16038         0.1
5         COMPUTATION overlapping MEMORY      564         0.0
################
                                                  name  sum (us)  max (us)  min (us)       stddev    mean (us)    kernel_type  rank
0    ncclKernel_AllGather_RING_LL_Sum_int8_t(ncclWo...  627683.0   10787.0      83.0  1651.592760  1687.319892  COMMUNICATION     0
1    ncclKernel_AllGather_RING_LL_Sum_int8_t(ncclWo...  644435.0   10884.0      82.0  1705.334758  1732.352151  COMMUNICATION     1
2    ncclKernel_AllGather_RING_LL_Sum_int8_t(ncclWo...  640631.0   10665.0      79.0  1700.774025  1722.126344  COMMUNICATION     2
3    ncclKernel_AllGather_RING_LL_Sum_int8_t(ncclWo...  643073.0   10834.0      81.0  1727.301230  1728.690860  COMMUNICATION     3
4    ncclKernel_AllGather_RING_LL_Sum_int8_t(ncclWo...  630605.0   10785.0      80.0  1656.166440  1695.174731  COMMUNICATION     4
..                                                 ...       ...       ...       ...          ...          ...            ...   ...
107                                    Memset (Device)    1134.0      13.0       1.0     0.807700     1.403465         MEMORY     3
108                                    Memset (Device)    1084.0       8.0       1.0     0.739841     1.341584         MEMORY     4
109                                    Memset (Device)    1073.0      14.0       1.0     0.818079     1.327970         MEMORY     5
110                                    Memset (Device)    1038.0       7.0       1.0     0.693866     1.284653         MEMORY     6
111                                    Memset (Device)    1064.0      13.0       1.0     0.779930     1.316832         MEMORY     7

[112 rows x 8 columns]
```