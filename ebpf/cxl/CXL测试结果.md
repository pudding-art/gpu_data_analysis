

# 测试环境

测试环境使用双路Intel(R) Xeon(R) Silver 4410Y,开启NUMA，单路配置如下：

12物理核，每个物理核2个超线程，**关闭hyper-threading技术**；

时钟频率：2.10GHz，**关闭turboboost**

L1 dcache: 1.1 MB

L1 icache: 768 KB

L2 cache: 48MB

L3 cache: 60MB

Local DDR Memory Type: DDR5-4800, Sumsung; 

Local CXL Memory Type: DDR4-3200, Micron;

Local DDR Memory Channel: 8

Local CXL Memory Channel: 2

Local DDR Memory Size: 单路32Gx8,每个channel上1条

Local CXL Memory Size: 单路16G，只有1个内存条，单通道

软件环境配置如下：

OS:Linux 6.15.4

GCC：11.4.0

## Stream/Stream2

stream具有4种不同类型的操作：

1. copy c[j]=a[j] 16byte

2. scale b[j]=scalar*c[j] 16byte

3. add c[j]=a[j]+b[j] 24byte

4. triad a[j] = b[j]+scalar*c[j] 24byte

单次操作统计的带宽比较直接，因为a/b/c都是double类型8个字节，以Triad为例，每次操作都访问了abc的一个元素，所以算作24字节。Triad测试核心代码如下：

![image-20240310015025450](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310015025450.png)

STREAM是用来测试系统内存带宽的，有必要了解当前系统的理论带宽：

单路是307.2GB/s；现在的带宽是280GB/s左右。

![image-20240310015109976](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310015109976.png)

***问题：为什么Stream测出的最大带宽和MLC测出的不一致？***

其实是一致的，只不过这里是双路CPU同时对自己的memory进行访问得到的结果。





### Stream配置

STREAM不是开箱即用的类型，需要根据不同的机器进行配置.

```bash
gcc -mtune=native -march=native -O3 -mcmodel=medium -fopenmp -DSTREAM_ARRAY_SIZE=<num> -DNTIMES=<num> -DOFFSET=<num> stream.c -o stream.o

gcc -mtune=native -march=native -O3 -mcmodel=medium -fopenmp -DSTREAM_ARRAY_SIZE=1000000000 -DNTIMES=10  stream.c -o stream.o

# -mtune=native -march=native
# 针对CPU指令的优化，由于测试编译机即运行机器，故采用native的优化方法，
```

**1.**   **STREAM_ARRAY_SIZE的设置**

以上内容主要是关于STREAM benchmark测试工具的使用说明和参数设置建议。其中提到了根据系统的缓存大小和系统计时器的粒度来确定STREAM需要的内存大小，建议调整STREAM_ARRAY_SIZE的数值以满足两个条件：

(1) 每个数组的大小至少是可用缓存内存的4倍；

(2) 确保timing calibration输出至少为20个时钟周期。

另外，版本5.10将默认数组大小从2百万增加到1千万，以适应L3缓存大小的增加。还提到了可以在编译时通过预处理器定义来设置数组大小，以便在不修改源代码的情况下进行参数调整。

**2.**   **NTIMES的设置**

NTIMES参数的一些规则和约定：

（1）  每个核心的测试会运行"NTIMES"次，并报告除第一次迭代之外的*最佳*结果，因此NTIMES的最小值为2；

（2）  对于NTIMES，没有规定最大允许的值，但是大于默认值的值不太可能显著提高报告的性能；

（3）  NTIMES也可以通过编译行进行设置，而无需更改源代码，例如使用"-DNTIMES=7；

**3.**   **OFFSET的设置**

通过修改"OFFSET"变量的值，可能会改变数组的相对对齐方式（尽管编译器可能会通过使数组在某些系统上非连续来改变有效的偏移量）。

当"OFFSET"变量的值为非零时，可以在一定程度上改变数组的对齐方式。这种做法在STREAM_ARRAY_SIZE设置为接近某个大的2的幂的值时特别有帮助。通过设置"OFFSET"变量，用户可以在编译时设置偏移量，而无需更改源代码，例如，使用"-DOFFSET=56"选项。

**4.**   **编译时的优化选项**

在进行编译之前，很多编译器可能会生成性能不佳的代码，在优化器进行优化后，性能会得到改善。建议在进行编译时使用优化选项。

（1）对于简单的**单核**版本，可以使用cc -O stream.c -o stream进行编译。这个命令在很多系统上都可以使用；

（2）如果要使用**多核**，需要告诉编译器遵循代码中的OpenMP指令，例如使用gcc -O -fopenmp stream.c -o stream_omp进行编译；开启后程序默认线程数为CPU线程数，也可以运行时也可以动态指定运行的进程数：export OMP_NUM_THREADS=12 #要使用的处理器数

（3）通过设置环境变量OMP_NUM_THREADS，可以在运行时控制程序使用的线程/核心数量；

（4）使用**单精度变量和算术**：如果想要使用单精度变量和算术，可以在编译时添加-DSTREAM_TYPE=float选项；

（5）TUNED预处理指令：TUNED预处理指令并不会做太多事情，它只是使代码调用单独的函数来执行每个核心。这些函数的版本是提供的简单版本，没有经过调优，只是提供预定义的接口，以便用调优的代码替换。

![image-20240310015450427](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310015450427.png)

> 以上定义开启多处理器运行环境；
>
> \#proagma omp parallel 用在一个代码段之前，表示这段代码将被多个线程并行执行；
>
> \#proagma omp atomic 指定一块内存区域被制动更新；
>
> \#proagma omp作为openmp编译指导语句的标识符；每个编译指导语句必须换行符结尾；长指令可以在行尾用符号\表示为下一行是续行，下一行可以接其他openmp的句子。![img](file:////Users/hong/Library/Group%20Containers/UBF8T346G9.Office/TemporaryItems/msohtmlclip/clip_image002.jpg)
>
> openmp句子区分大小写，所有编译指导语句均用小写字母表示；每条指令只能有1个指令名称；注释语句和编译指令语句不能出现在同一行。



```bash
# Stream运行指令测试
for i in {1..96}; do OMP_PLACES=cores OMP_PROC_BIND=close KMP_AFFINITY=granularity=fine,compact,1,10 OMP_NUM_THREADS=$i ./stream.134M | grep "Triad"; done
```

<!--grep -E 'word1|word2|word3' filename，-E用于启用正则表达式。-->

![image-20240310161719061](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310161719061.png)

已经平均30次.

![image-20240312134049267](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312134049267.png)

![image-20240312134717754](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312134717754.png)

![image-20240312134521057](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312134521057.png)

![image-20240312134621454](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312134621454.png)



----

### 参考

https://www.cnblogs.com/zwh-Seeking/p/17729385.html

https://zhuanlan.zhihu.com/p/510954835

https://ark.intel.com/content/www/cn/zh/ark/products/232376/intel-xeon-silver-4410y-processor-30m-cache-2-00-ghz.html

常用的Stress/Performance工具：

https://benjr.tw/532

CPU/内存/磁盘/网络/Redis/MQ/数据库测试工具合集：

https://www.cnblogs.com/zwh-Seeking/p/17711365.html

Linux系统性能测试工具（三）——内存性能综合测试工具lmbench 原创

https://blog.51cto.com/u_15748605/5566552

[https://foxsen.github.io/archbase/%E8%AE%A1%E7%AE%97%E6%9C%BA%E7%B3%BB%E7%BB%9F%E6%80%A7%E8%83%BD%E8%AF%84%E4%BB%B7%E4%B8%8E%E6%80%A7%E8%83%BD%E5%88%86%E6%9E%90.html](https://foxsen.github.io/archbase/计算机系统性能评价与性能分析.html)

Linux性能基准测试工具及测试方法：https://clay-wangzhi.com/cloudnative/stability/benchmark/sysbench.html

Stream官网：https://www.cs.virginia.edu/stream/ref.html

Substainable Memory Bandwidth in Current High Performance Computers https://www.cs.virginia.edu/~mccalpin/papers/bandwidth/bandwidth.html

Stream benchmark测试及相关参数说明：https://www.twblogs.net/a/5b8a945a2b71775d1ce7dfc9/?lang=zh-cn

评估内存性能（此网站也有很多其他知识点）：https://goodcommand.readthedocs.io/zh-cn/v1.0.0/mem_benchmark/

从stream的多线程协同效率说起

https://zhuanlan.zhihu.com/p/43588696

高性能计算之OpenMP（二）https://blog.csdn.net/lv15076050705/article/details/122107882

\#program编译器指令详解

https://blog.csdn.net/Primeprime/article/details/105110827

Intel C++ Compiler(icc)与gcc对比有什么优缺点？https://www.zhihu.com/question/21675828

SDB：安装和使用Intel C++ Compiler

[https://zh.opensuse.org/SDB:%E5%AE%89%E8%A3%85%E5%92%8C%E4%BD%BF%E7%94%A8Intel_C%2B%2B_Compiler](https://zh.opensuse.org/SDB:安装和使用Intel_C%2B%2B_Compiler)

makefile编译器除了gcc还有什么？Clang，LLVM，icc，Microsoft Visual C++等；

[https://juejin.cn/s/makefile%E7%BC%96%E8%AF%91%E5%99%A8%E9%99%A4%E4%BA%86gcc%E8%BF%98%E6%9C%89%E4%BB%80%E4%B9%88](https://juejin.cn/s/makefile编译器除了gcc还有什么)

clang 3.8+ -fopenmp on linux:ld找不到-lomp

https://cloud.tencent.com/developer/ask/sof/104578962

objdump命令详解

https://blog.csdn.net/qq_41683305/article/details/105375214

Intel White Paper, "Measuring Memory Bandwidth On the Intel® Xeon® Processor 7500 series platform"

 清华大学高性能计算导论实验文档：

https://lab.cs.tsinghua.edu.cn/hpc/doc/faq/binding/

从stream的多线程协同效率说起

https://zhuanlan.zhihu.com/p/43588696

Top-down性能分析实战

https://zhuanlan.zhihu.com/p/35124565

## MLC

Intel Memory Latency Checker（Intel MLC）是一个用于测试延迟和带宽如何随系统负载的增加而变化；实现方法是MLC创建压测主机逻辑处理器数量减1个线程，然后使用这些线程生成压测流量，余下1个vCPU用于运行一个测试延迟的线程。 

软件版本：

mlc_v3.9a

内存延迟是指系统在发出内存读取请求后，等待内存响应返回的时间，包括了内存访问请求在内存控制器中排队等待，内存模块中的存取时间等；

RPQ(Read Pending Queue)延迟，是内存访问请求在内存控制器中排队等待的时间；

--latency_matrix 仅输出本地和交叉socket内存延迟

--bandwidth_matrix 仅输出本地和交叉socket内存带宽

--peak_injection_bandwidth 仅输出在不同读写速率下本地内存访问的尖峰内存带宽

--idle_latency 仅输出平台的空闲内存延迟

--loaded_latency 仅输出平台有负载的内存延迟

--c2c_latency 仅输出平台hit/hitm延迟



### idle_latency测试

#### idle_latency测试原理

idle_latency模式下系统没有其他负载工作。执行相关负载，类似指针追逐。初始化一个buffer，**buffer每行64byte(cacheline大小）**，指向下一行/地址（所以每个64byte中存储的是下一个地址？），其实是一个缓存行的粒度。初始化的这部分地址空间放在CXL memory或者其他待测内存中（访问一块内存，然后按照内存中的地址再次访问一个内存，**不断的执行load读取指令**）

该工具创建一个计时器，然后在执行百万个load指令后停止计时，将此阶段运行load指令数和总运行时间记录下来，然后进行测试。**（这里的百万个load指令怎么计算？是访问过buffer所有的地址之后终止吗？）**

该工具对load指令落在cache还是memory没有概念，所以需要手动初始化buffer大小，buffer size=4xLLC size，确保指令LLC miss最终落到memory上。（其实感觉也不是初始化这段地址空间，只是声明要在这段空间内工作）。

默认情况下，MLC禁用硬件预取器（prefetcher），并且默认是顺序访问(Sequential)。由于硬件预取器无法在所有环境中禁用，所以提供了random的测试方法。初始化buffer中的每个cacheline长度的字段指向一个随机生成的值。同时为了减少TLB miss的影响，并不是在分配的整个buffer中随机访问，而是将buffer切分成块（是否相等没说，切分的策略也没说），每个块内随机访问，块间顺序访问。

***问题一：idle_latency测试和latency_metric有什么区别吗？***

应该没有区别，idle_latency是需要用户自己控制当前机器没有其他负载运行，latency_metric就是直接测量当前的系统延迟，没有考虑idle的状态。

![image-20240308211104529](/Users/hong/Library/Application%20Support/typora-user-images/image-20240308211104529.png)

***问题：这里MLC的延迟比较高是因为Intel MLC的串行化内存访问无法直接利用连接NUMA节点的UPI接口的全双工功能？***

---------------------------



#### 测试结果

```bash
# 测试系统在unloaded idle情况下的内存访问延迟
# CPU利用率并没有显著变化，而且CPU始终是绑定在NUMA0上
# -r 控制顺序访问or随机访问
hwt@cxl-2288H-V7:~/cc_test/mlc_v3.9a/Linux$ sudo ./mlc --latency_matrix -r
Intel(R) Memory Latency Checker - v3.9a
Command line parameters: --latency_matrix -r 

Using buffer size of 2000.000MiB
Measuring idle latencies (in ns)...
                Numa node
Numa node            0       1       2
       0         117.4   184.3   561.7
       1         186.0   117.9   391.0
       
# 顺序访问的数据
sudo ./mlc --latency_matrix 
```

![image-20240308215236983](/Users/hong/Library/Application%20Support/typora-user-images/image-20240308215236983.png)

***问题：延迟如何归一化？带宽可以按照理论带宽直接除以8来计算，但是延迟不一定是整数直接除以8计算。***

DDR Remote归一化到本地DDR Local没有什么问题，但是CXL Remote和CXL Local就比较难以归一化。上面论文中的MLC结果是本地的3倍左右，单通道的DDR Local延迟是会增加还是降低？

https://www.elecfans.com/d/1897631.html

上述文章中有提到“从单通道变双通道也使得DDR5延迟更低、效率倍增”。所以还是会有区别，应该会比现在的测出来的内存延迟更高，论文中是3倍左右，如果本地DDR内存变成单通道，应该也差不多是3倍。

综上所述，延迟的测试应该是没有问题的。

***问题：没有关闭系统的hyper-threading进行测试。关闭超线程？（先不关闭做一些实验）***

系统配置中，DDR-Remote为了和CXL memory保持一致，使用了单通道的内存；还有就是强制关闭了hyper- threading。

```bash
# 操作系统下关闭CPU超线程
echo off > /sys/devices/system/cpu/smt/control
```

***问题：如何设置系统内存单通道还是多通道？***

~~（从系统软件层面如何关闭还不知道）~~不能在软件层面操作，只能BIOS设置或者从物理层面直接拔掉内存条进行测试。~~现在的服务器是每通道双列DIMM还是每通道单列DIMM（但是不管单列双列，现在就是每个通道有一个DIMM条），如果是单通道双DIMM条，DIMM条之间的切换也会对最终结果造成影响~~。现在的服务器自身是支持每通道双列DIMM条，一个Primary DIMM（必须），一个Secondary DIMM，但是只插了一个，所以目前不需要考虑DIMM条切换导致速率下降。

***问题：如果不关闭多通道，直接使用pcm-tools或者perf监控单通道的读写数据，直接输出？但是如果是这样的话，记录的数据就不是MLC算出来的了，而是实际的数据，而且这些采集工具是变化的，采集粒度是多少，如何计算最终的单通道结果也是一个问题。确实可以监控单个通道上的流量变化，但是正因为是变化的，没有办法统计一个最终的值，定期采样选最大的？***必须关闭多通道。

***问题：idle_latency测试无法使用numactl绑定具体的CPU？***目前使用numactl绑定都会失效。目前还不知道怎么调整，感觉也不像是利用了所有的CPU。可以使用-c参数 ，将延迟测试的线程pin到指定CPU，所有内存访问都将从这个特定的CPU发出。但是只能设置单个的-c0-23,或者是全部-a没有其他的选择。绑定单个CPU core测试结果和latency_metric差不多，看一下-a是不是也一致(-a只能和--latency_matrix参数配合使用），如果一致，则也可以验证-loaded_latency中本地DRAM和远程DRAM的带宽变化情况的准确性。

```bash
hwt@cxl-2288H-V7:~/cc_test/mlc_v3.9a/Linux$ sudo numactl -m 0 ./mlc --latency_matrix -r -a
Intel(R) Memory Latency Checker - v3.9a
Command line parameters: --latency_matrix -r -a 

Using buffer size of 2000.000MiB
Measuring idle latencies (in ns) for all cores...
                Numa node
CPU          0       1       2
     0   117.8   184.4   561.9
     1   117.3   184.2   561.7
     2   116.4   184.8   561.9
     3   117.1   185.4   562.5
     4   116.1   184.2   561.2
     5   118.9   187.3   564.8
     6   116.4   183.2   560.7
     7   116.3   184.6   561.3
     8   116.6   187.2   564.1
     9   116.9   188.0   564.9
    10   116.1   185.4   561.9
    11   116.9   188.4   566.0
    12   185.5   119.0   391.1
    13   185.8   117.8   391.0
    14   186.2   117.5   391.0
    15   184.9   116.6   390.9
    16   185.8   116.8   391.0
    17   188.0   119.4   391.0
    18   186.8   117.8   391.0
    19   187.7   118.2   391.0
    20   184.1   116.4   391.0
    21   185.1   116.4   391.0
    22   188.1   117.2   391.0
    23   187.9   116.9   391.1
```

----------

### bandwidth

1. load指令执行：为了测量带宽，MLC执行未被消耗的load指令（即load返回的数据不会在后续指令中被使用），这使得MLC能够生成尽可能大的带宽。

   > load的数据没有被继续使用，即数据加载到缓存中，但是每当下一个数据读的时候都要从内存中读数据，这些负载指令会频繁的向内存请求数据。这些负载指令主要用于产生内存访问流量而不是实际数据处理。如果是实际处理的话肯定想更多的命中cache。

2. 软件线程：MLC给每个物理core分配一个独立的软件线程，每个线程独立执行，**访问的地址是独立的**，线程之间不共享数据。

3. buffer大小：buffer大小决定了MLC测量的是L1/L2/L3还是内存带宽，如果测量内存带宽，MLC应该使用较大的缓冲区（4x）

4. 流量模式：主要是设置不同的读写比例。

5. store指令：store如果没有non-temporal，store=1read+1store. 主要和cache有关。

   > When the processor executes a store instruction, a read transaction is issued to obtain exclusive ownership (aka Read-For-Ownership (RFO) transaction) of the line. The store data is merged with the line that is read and kept in the cache and later the modified line is evicted and written back to memory. Thus, the store instruction translates into one read and one write as seen by the memory controller.

6. B/W Report: 最终展示的带宽是内存控制器看到的读取和写入带宽之和。

***问题：buffer的设置是给每个线程200MB？还是一共200MB？是读写各200MB还是读写平均分200MB？***默认情况是读写各分配244.14MB的空间。

```bash
hwt@cxl-2288H-V7:~/cc_test/mlc_v3.9a/Linux$ sudo ./mlc --bandwidth_matrix 
Intel(R) Memory Latency Checker - v3.9a
Command line parameters: --bandwidth_matrix 

Using buffer size of 244.141MiB/thread for reads and an additional 244.141MiB/thread for writes
Measuring Memory Bandwidths between nodes within system 
Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)
Using all the threads from each core if Hyper-threading is enabled
Using Read-only traffic type
                Numa node
Numa node            0       1       2
       0        143146.9        63453.9  7120.2
       1        63465.2 143120.3        19489.0
       
# 全读流量，244.14MB/thread，所有线程都打开，如果超线程打开的话应该是48个threads，但访问的时候不是
# 访问的时候因为是矩阵，点对点访问，所以不是全部threads
```

查看本机DDR DRAM的详细信息：

```bash
sudo dmidecode -t 17
...
Handle 0x0020, DMI type 17, 92 bytes
Memory Device
        Array Handle: 0x0007
        Error Information Handle: Not Provided
        Total Width: 80 bits
        Data Width: 64 bits
        Size: 32 GB
        Form Factor: DIMM
        Set: None
        Locator: DIMM140 J26
        Bank Locator: _Node1_Channel4_Dimm0
        Type: DDR5
        Type Detail: Synchronous Registered (Buffered)
        Speed: 4800 MT/s
        Manufacturer: Samsung
        Serial Number: 4526CF2E
        Asset Tag: 2317 0620Y005
        Part Number: M321R4GA3BB6-CQKET            
        Rank: 2
        Configured Memory Speed: 4000 MT/s
        Minimum Voltage: 1.1 V
        Maximum Voltage: 1.1 V
        Configured Voltage: 1.1 V
        Memory Technology: DRAM
        Memory Operating Mode Capability: Volatile memory
        Firmware Version: 0000 
        Module Manufacturer ID: Bank 1, Hex 0xCE
        Module Product ID: 0xCE00
        Memory Subsystem Controller Manufacturer ID: Unknown
        Memory Subsystem Controller Product ID: Unknown
        Non-Volatile Size: None
        Volatile Size: 32 GB
        Cache Size: None
        Logical Size: None
...
```

![image-20240309100856399](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309100856399.png)

从配置信息可以看到V7服务器的内存条：DIMM Synchronous Registered (Buffered) 4800MHz(0.2ns), 有16条，每个CPU目前连接8条（实际可以连16）,Speed=4800MT/s, Configured Memory Speed：4000MT/s，后者应为内存模块被配置为运行的速度（这个速度可以更改吗？） DPC（Data Per Channel）

```bash
root@cxl-2288H-V7:/home/hwt/cc_test# lscpu | grep "Socket(s)" -A1
Socket(s):                  2
Steppint:                   8
```

$\color{Blue}{8x4000x64/8 = 256GB/s}$ 应该是实际能达到的理论带宽最大值

8x4800x64/8 = 307.2GB/s

***问题：DDR内存实际运行速度怎么配 ？为什么bandwidth_matrix测出的内存带宽才是实际内存带宽的50%？为什么bandwidth_matrix测出的带宽是peak_bandwidth的1/2?为什么bandwidth_matrix跑满了全部的CPU core还是这么慢？***

```bash
hwt@cxl-2288H-V7:~/cc_test/mlc_v3.9a/Linux$ ./mlc --peak_injection_bandwidth
Intel(R) Memory Latency Checker - v3.9a
Command line parameters: --peak_injection_bandwidth 

Using buffer size of 244.141MiB/thread for reads and an additional 244.141MiB/thread for writes
*** Unable to modify prefetchers (try executing 'modprobe msr')
*** So, enabling random access for latency measurements

Measuring Peak Injection Memory Bandwidths for the system
Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)
Using all the threads from each core if Hyper-threading is enabled
Using traffic with the following read-write ratios
ALL Reads        :      280392.7
3:1 Reads-Writes :      311001.0
2:1 Reads-Writes :      306843.1
1:1 Reads-Writes :      287711.6
Stream-triad like:      262420.0
```

猜测，bandwidth_matrix访问内存是所有CPU上的core访问同一个NUMA节点上的内存，而peak_bandwidth中的CPU访问的是自己的NUMA节点上的内存，NUMA0+NUMA1的总带宽。但是如果是所有CPU core访问一个NUMA节点上的内存，那应该出现瓶颈啊？？怎么计算的这里？？Remote+Local？

应该是没问题，因为看了Peak Injection memory的带宽就是两路CPU分别访问自己的内存，而bandwidth_matrix和loaded_latency都是CPU访问一个位置的内存。

bandwidth_matrix DDR Local在160GB/s左右，loaded_latency 00000 12也在160GB/s左右，所以是对的。

![image-20240309100652808](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309100652808.png)

跑满单通道读写在18GB/s左右

***问题：DDR-Remote的带宽和Demystifying论文中比例相差无几，但是为什么DDR Remote限制在60GB/s左右？DDR Local目前的得到的带宽是双向带宽还是单向带宽？***

首先查一下UPI的带宽。 Intel(R) Xeon(R) Silver 4410Y UPI参数如下：

![image-20240309182857661](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309182857661.png)

![image-20240309190938344](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309190938344.png)

16GT/s x 16/8 x 2 = 64GB/s (如果有效带宽是16bit)，还是需要实测一下真实的UPI带宽，确认瓶颈出现在哪里。这里使用Intel PCM工具检测UPI流量。在执行./mlc --bandwidth-matrix同时执行以下指令：

```bash
# 每隔0.1s输出一次数据；
# -i=10 0.1s内输出10次数据
# -csv 输出信息到csv文件
sudo ./pcm 0.1 -csv=test.csv 
```

![image-20240309193126720](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309193126720.png)

输出文件显示当前UPI两条链路的带宽利用率如上，两路输出达到35.8GB/s，上线接近70GB/s，基本达到峰值，所以应该是UPI带宽的限制。

***问题：为什么本地带宽143GB/s左右，才达到理论带宽的56%左右***

***先用不同的工具测试一下，是不是所有工具的算法达到的本地带宽都是这么多。首先排除工具的问题。***

> 内存带宽性能偏低问题处理和经验总结：
>
> https://blog.csdn.net/a1234333/article/details/130323225
>
> 首先是同理论带宽数值进行比对，确定目标判断差异；如果差异较大，最快速的是查看影响内存带宽性能最大的一个BIOS选项，也就是NUMA节点的设置，如果打开之后差距比较小，需要进行调优，可以将BIOS下的NUMA和超线程关闭，并考虑CPU性能模式的设置；内存插法也会影响（通常来说机器默认出厂的内存插法会按照服务器厂商对该数量的推荐插法来，但是推荐插法一般是CPU厂商提供的。服务器厂商的插法不一定就是正确的，可能会出现错误的情况，直接咨询相关CPU厂商确认）；如果以上均排除过，也可以看下不同编译器的stream工具的结果是否存在差异，不排除一些不够成熟的CPU平台会有这样的问题；如果这种问题不是普遍情况，而是某个机器上 的个例情况，那理论上和异常的内存有关，这个时候一方面可以通过更换内存条来确认，也可以用内存压测工具确认是否有异常。

参考：

【1】详解服务器内存带宽计算和使用情况测量https://blog.yufeng.info/archives/1511 

【2】CPU/内存监视器https://blog.yufeng.info/archives/1511

-------

### peak_injection_bandwidth测试

![image-20240309202718460](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309202718460.png)

论文中将所有情况下的带宽都归一化到控制器后面接的内存介质的理论带宽。现在DDR5-4800（4000）理论带宽是256GB/s，CXL内存带宽是DDR4 3200的带宽，即25.6GB/s。

首先在peak_injection_bandwidth条件下测试，由于此中情况下无法指定具体的CPU，所有的core全都在运行，所以结果如下（Only-Read是之前带宽的2倍，因为2CPU都可以访问本地内存，第一种情况没有限制就是跑满，第三种限制只能访问一个NUMA的memory很明显就可以看出结果1/2，所以测试的结果应该是没有什么问题：

```bash
hwt@cxl-2288H-V7:~/cc_test/mlc_v3.9a/Linux$ sudo ./mlc --peak_injection_bandwidth
Intel(R) Memory Latency Checker - v3.9a
Command line parameters: --peak_injection_bandwidth 

Using buffer size of 244.141MiB/thread for reads and an additional 244.141MiB/thread for writes

Measuring Peak Injection Memory Bandwidths for the system
Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)
Using all the threads from each core if Hyper-threading is enabled
Using traffic with the following read-write ratios
ALL Reads        :      286145.2
3:1 Reads-Writes :      311492.2
2:1 Reads-Writes :      307483.4
1:1 Reads-Writes :      282564.6
Stream-triad like:      262715.0

hwt@cxl-2288H-V7:~/cc_test/mlc_v3.9a/Linux$ sudo numactl -c 1 -m 2 ./mlc --peak_injection_bandwidth
Intel(R) Memory Latency Checker - v3.9a
Command line parameters: --peak_injection_bandwidth 

Using buffer size of 244.141MiB/thread for reads and an additional 244.141MiB/thread for writes

Measuring Peak Injection Memory Bandwidths for the system
Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)
Using all the threads from each core if Hyper-threading is enabled
Using traffic with the following read-write ratios
ALL Reads        :      18614.3
3:1 Reads-Writes :      15387.0
2:1 Reads-Writes :      14047.7
1:1 Reads-Writes :      13191.3
Stream-triad like:      13384.5

hwt@cxl-2288H-V7:~/cc_test/mlc_v3.9a/Linux$ sudo numactl -c 1 -m 0 ./mlc --peak_injection_bandwidth
Intel(R) Memory Latency Checker - v3.9a
Command line parameters: --peak_injection_bandwidth 

Using buffer size of 244.141MiB/thread for reads and an additional 244.141MiB/thread for writes

Measuring Peak Injection Memory Bandwidths for the system
Bandwidths are in MB/sec (1 MB/sec = 1,000,000 Bytes/sec)
Using all the threads from each core if Hyper-threading is enabled
Using traffic with the following read-write ratios
ALL Reads        :      160510.8
3:1 Reads-Writes :      168655.3
2:1 Reads-Writes :      160180.4
1:1 Reads-Writes :      146784.7
Stream-triad like:      149288.2
```

所以这里只能算出本地DRAM和CXL的效率。如果想要控制核数，还是要使用loaded_latency进行测试。场景就是所有的core都用于访问NUMA1的内存，以及NUMA1上的CXL Memory的结果（类似论文中的图用loaded_latency测试去做）：

![image-20240309205846951](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309205846951.png)

**Efficiency of maximum sequential memory access bandwidth across different memory types.**

------

###  loaded_latency测试

也就是生成了其他负载下的延迟，但是在injection为00000的时候, 此时的系统延迟也和idle latency不同。

负载生成线程/带宽生成线程，主要功能是尽可能生成更多的内存引用。

带宽生成线程会定期降低带宽生成的速度，以测量不同负载条件下的延迟。默认情况下，运行延迟线程的核心会禁用硬件预取器，因为延迟线程会进行顺序访问。但是，生成带宽的核心会启用预取器。需要注意的是，MLC报告的带宽也**包括延迟线程的带宽**。

**每个线程都为读取操作分配一个缓冲区，为写入操作分配一个单独的缓冲区（没有任何线程之间共享数据）。**通过适当调整缓冲区的大小，可以确保引用在任何特定的缓存级别上得到满足或由内存提供服务。

#### Test 1: All-Reads Bandwidth & Latency core scaling(Sequential/Random)

```bash
#!/bin/bash
# 以下内容获得带宽,sequential
MLC="./mlc"     # MLC command
OPERATION="R" # Read-only as default
DRATION=5     # Run 5 seconds as default
LOW=12
BUFFER=200000
# CPU_BIND=$1  # 0/1
# MEM_BIND=$2 # 0/1/2
# 可以上面两个参数放在下面的numactl中测试4种情况下的数据，但是先保证有数据，然后再看
function memorybw_core()
{
	core_count=$1
	# echo "core_count=${core_count}"
	# echo "2^(${core_count}+1)-2^${LOW}"
	mask=0x$(echo "obase=16;2^(${core_count}+1)-2^${LOW}" | bc)
	# echo "mask=${mask}"
	
	bw=$(${MLC} --loaded_latency -d0 -${OPERATION} -t${DRATION} -b${BUFFER} -T -m$mask | grep 00000 | awk '{print $2 $3}') # grep 00000 在没有其他负载的时候处理
	# echo "${bw}"
	# print $3 ---> bandwidth
		echo $bw
	}

for i in {12..23}
do
	bw=$(memorybw_core $i)
	echo "#$i $bw"
done  

LLC 30MB, buffer=200MB, 单核测试DDR本地内存，CXL内存的到的结果显示
sudo numactl -membind=2 ./mlc --loaded_latency -d0 -W6 -r -b200000 -m2^23 | grep 0000 | awk '{print $2 $3}'
```

-r Initialize the buffer (used by latency thread) with pseudo-random values so the access pattern to memory will be random for latency measurement. For random access in loadgeneration threads, use option –U. This option is valid in idle_latency, latency_matrix and loaded_latency modes.

![image-20240309221447909](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309221447909.png)

![image-20240309221501021](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309221501021.png)

根据以上结果显示，Sequential和Random模式下的带宽基本没有区别。（所有cores都启动访问达到的最大带宽在160-170GB/s左右）以上12cores均是单个CPU已经跑到100%了对内存发起多个loads请求下的结果。

![image-20240309221859769](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309221859769.png)

***问题：需要将上述脚本的某些地方完善，并且将绘图脚本也写到当前的脚本中？***

![image-20240309233022666](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309233022666.png)

![image-20240309233104776](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309233104776.png)

***问题：上面测试在NUMA1访问NUMA0的延迟竟然比NUMA1访问本地延迟还要低；但是在NUMA0上就是恰好相反的状态，延迟也是上升的状态？下图是NUMA0节点上的测试数据，看起来就比较正常（Random下就不进行测试了，因为结果都差不多）***

虽然趋势不明显，但是延迟也是有略微升高的。所以问题仅存在于为什么本地内存带宽要比远端numa内存带宽低？

![image-20240309233449611](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309233449611.png)

***问题：是否应该将延迟路径分解一下，分析下原因？***

***问题：多核情况下是怎么并行处理的？***

#### Test 2: Bandwidth & Latency core scaling with various read and write ratios(Sequential/Random)

不需要随着core增加做实验了，上面已经有all-reads操作，后面其实趋势都差不多。这里只需要做一组all cores下所有不同读写比例的CXL Local, CXL Remote, DDR Local, DDR Remote延迟和带宽即可(Sequential/Random)。

***问题：没有W4这个参数对应的值，输出结果中第四个要删除；***

***问题：还有一个问题，看起来不是All-Reads情况下，带宽要更高，这是为什么？***

![image-20240310141033347](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310141033347.png)

**问题：为什么2:1的nt-store带宽要比2:1的store带宽低？为什么CXL remote memory读的比例越高带宽越低？**

**问题：buffer都是固定的200MB，那不同读写比例的时候如何分配这个buffer？是平均分给读写吗？所有线程同时进行读写吗？读写比例是多少？是不是t参数的问题？**

#### Test 3: Memory access efficiency across various read and write(Sequential/Random)

只需要考虑下图的几种读写测试的结果就可以了🐶

![image-20240309202718460](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309202718460.png)

All-read看上一个测试，从这个测试中找3:1-RW，2:1RW，1:1RW。延迟不用看了，作用不大，主要关注带宽。

![image-20240310140512948](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310140512948.png)

***问题：为什么本地all-read带宽比其他读写加起来的要低？怀疑一点就是默认分配的buffer不同，导致的结果差异。all-read当时设置的是200MB的buffer，但是后面的不同比例的读写带宽buffer可能不是这个数字。如果本地和远程内存都使用单通道应该可以排除这个问题。***

![image-20240310140812870](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310140812870.png)

```

```



## 参考

非常牛逼的分析了访存过程中每个部分的延迟：

https://sites.utexas.edu/jdm4372/2011/03/10/memory-latency-components/

Demysifying CXL memory with Genuine CXL systems

Perf 综合分析工具介绍https://hhb584520.github.io/kvm_blog/2017/01/01/perf_all.html

Top-down性能分析模型https://zhuanlan.zhihu.com/p/34688930

使用 Intel 开源工具 MLC 压测处理器与内存之间的延迟、吞吐量等指标

https://ywjsbang.com/os/202210/pressure_mlc/

**MLC内存测试结果解读到CPU架构设计分析**

https://zhuanlan.zhihu.com/p/447936509

MLC-Intel内存延迟测试工具https://huataihuang.gitbooks.io/cloud-atlas/content/server/memory/mlc_intel_memory_latency_checker.html

服务器内存测试工具MLC介绍https://www.ctyun.cn/developer/article/474706450513989

MLC使用手册 

## 问题

![image-20240309222936219](/Users/hong/Library/Application%20Support/typora-user-images/image-20240309222936219.png)

之前的脚本输出不了latency的值，因为使用-T关闭了latency的输出😂

![image-20240310150443258](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310150443258.png)

特别奇怪的现象，在对NUMA1进行测试的时候，竟然有这么高的CXL Read Throughput？

![image-20240310150619915](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310150619915.png)

对numa1脚本的监控也显示没有什么问题。

## LMbench

`Lmbench` 是一款简易可以移植的内存测试工具，其主要功能有，带宽测评（读取缓存文件、拷贝内存、读/写内存、管道、TCP），延时测评（上下文切换、网络、文件系统的建立和删除、进程创建、信号处理、上层系统调用、内存读入反应时间）等功能。

执行单个测试用例：进入`/bin`目录下执行对应用例即可

- 这里主要关心带宽测试`bw_mem`和延迟测试`lat_mem_rd`
- `bw_mem`
  - 参数说明
    - `-P`：指定并行度（同时读写的线程数），默认为1
    - `-W`：指定预热时间（预热缓存，避免影响内存测试结果），默认为2s
    - `-N`：指定重复测试次数，默认为10次
    - `size`：测试数据块大小，单位Byte
    - `type`: 测试类型
      - `rd` 顺序读取
      - `wr` 顺序写入
      - `frd`随机读取
      - `fwr`随机写入
      - `cp`单线程复制操作
      - `fcp`随机复制操作
      - `rdwr`读写交替进行
      - `bzero`填充0操作
      - `bcopy`内存拷贝操作
  - 示例：`./bw_mem -P 4 -W 3 -N 3 16M rd`，表示并行度4，预热时间3s，重复测试3次，读取16M大小数据块
- `lat_mem_rd`
  - 参数说明
    - `-P`：指定并行度，默认为1
    - `-t`：指定为随机访问，否则为顺序访问
    - `-N`：指定重复测试次数，默认为10次
    - `size`：访问的最大数据块，单位MB
    - `stride`：访问步长，单位Byte，默认64B
  - 示例：`./lat_mem_rd -P 2 -t -N 3 128 256`，表示并行度2，随机访问，重复测试3次，最大访问到128MB数据，步长为256（注意stride可以写多个，会依次进行测试，例如`./lat_mem_rd 128 64 256 1024`，会依次测试步长为64B、256B、1024B）

#### 问题

编译运行出现以下错误：

![image-20240310172628305](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310172628305.png)

apt install libntirpc-dev

scripts/build中添加如下内容：

![image-20240310172642109](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310172642109.png)

make at top directory但是失败了

![image-20240310172658301](/Users/hong/Library/Application%20Support/typora-user-images/image-20240310172658301.png)

成功，make results即可

在1-12 CPU cores中实现对以上不同类型的读写带宽，buffer设置为200MB，TIMES=10：

##### CPU的卸载方法

用cpu0举例，其他cpu核方法一致，测试cpu0对内存的读写速度；拔掉其他的cpu核，只保留cpu0在线

```bash
echo > 0 /sys/devices/system/cpu/cpu(n)/online # n按照当前系统中的cpu core数量取上限
cat /sys/devices/system/cpu/cpu(n)/online # 分别读取各个cpu line节点的值，如果是0表示拔核成功
cat /sys/devices/system/cpu/online # 查看哪个cpu在线
```

### 测试原理

如果光光使用lat_mem_rd来跑得出一个结果, 不了解测试细节的话, 很多东西都理解还不深刻, lat_mem_rd的延迟测试的代码是这样写的

```C++
#define    ONE            p = (char **)*p;
#define    FIVE    ONE ONE ONE ONE ONE
#define    TEN            FIVE FIVE
#define    FIFTY    TEN TEN TEN TEN TEN
#define    HUNDRED    FIFTY FIFTY

    while (iterations-- > 0) {
        for (i = 0; i < count; ++i) {
            HUNDRED;
        }
    }
```

用指针指向下一个内存地址空间来循环访问, 比如说0.00049 1.584, 这个结果就是在512字节范围内, 步长16来一直循环访问, 最后时间除以访问次数就是延迟。

- 测量不同内存大小和跨度的内存读取延迟。结果以每次加载纳秒为单位报告;
- 测量整个内存层次结构，包括板载缓存延迟和大小、外部缓存延迟和大小、主内存延迟和TLB未命中延迟。
- 仅测量数据访问；指令缓存没有测量。
- 基准测试作为两个嵌套循环运行。外环是步幅大小。内部循环是数组大小。对于每个数组大小，基准创建一个指针环，指向前一个步长。遍历数组由p = (char **)*p;
- 数组的大小从 512 字节开始。对于小尺寸，缓存会起作用，加载速度会快得多

范围超过L1 cache的32k的时候, 会有一个阶级变化。



测试主要流程：

1. 解析命令参数；
2. 根据输入的命令更新测试参数（步长，最大访问数据块大小等）
   这里需要说明的是，除去最大访问数据块的大小必须设置之外，其他的选项都被赋予了默认值。
3. loads函数进行延迟测试。该函数就是最主要的函数了。测试是通过两层嵌套循环完成的：外层循环是每次访问的range大小（就是测试结果左侧那一列），最小值是0.00049M（512K），循环增加至所设置的最大数据块大小。内层循环是访问次数count，count的计算是由range与stride（步长）共同决定的
   结果计算就是访问某个数据块大小所用的时间除以访问次数count就得到了延迟大小。对于每次循环，基准创建了一个链表，指针指向前一个步长，数组的遍历通过指针完成；
4. 结果打印

#### 参考：

性能测试工具lmbench的使用方法以及解析运行结果

https://blog.csdn.net/qq_36393978/article/details/125989992

lmbench fatal error: rpc/rpc.h: No such file or directory

https://blog.csdn.net/qq_38963393/article/details/131715454

fix compilation error 'fatal error: rpc/rpc.h: No such file or directory' #16

https://github.com/intel/lmbench/issues/16

lmbench内存延迟测试代码分析https://developer.aliyun.com/article/591720

## Redis

```bash
hwt@cxl-2288H-V7:~/cc_test/lmbench/bin/x86_64-linux-gnu$ java -version
openjdk version "11.0.22" 2024-01-16
OpenJDK Runtime Environment (build 11.0.22+7-post-Ubuntu-0ubuntu222.04.1)
OpenJDK 64-Bit Server VM (build 11.0.22+7-post-Ubuntu-0ubuntu222.04.1, mixed mode, sharing)
# 安装maven
sudo apt-get install maven
# 安装YCSB
git clone http://github.com/brianfrankcooper/YCSB.git
cd YCSB
hwt@cxl-2288H-V7:~/cc_test/YCSB$ mvn -pl com.yahoo.ycsb:redis-binding -am clean package
[INFO] Scanning for projects...
[ERROR] [ERROR] Could not find the selected project in the reactor: com.yahoo.ycsb:redis-binding @ 
[ERROR] Could not find the selected project in the reactor: com.yahoo.ycsb:redis-binding -> [Help 1]
[ERROR] 
[ERROR] To see the full stack trace of the errors, re-run Maven with the -e switch.
[ERROR] Re-run Maven using the -X switch to enable full debug logging.
[ERROR] 
[ERROR] For more information about the errors and possible solutions, please read the following articles:
[ERROR] [Help 1] http://cwiki.apache.org/confluence/display/MAVEN/MavenExecutionException
# 出现以上输出说明解压时已经编译好了，再编译会出错
# 但是之前是由python2编译出来的，版本较低，直接使用会报错
# 浅拷贝
git clone --depth 1 https://github.com/brianfrankcooper/YCSB
cd YCSB
mvn -pl site.ycsb:redis-binding -am clean package
# 之后因为需要很多乱七八糟的库，不建议直接mvn clean package，部分编译比较好,以上是编译Redis
# 后，就可以使用ycsb了，因为不管是bat文件还是sh文件，维护都不够，github上一堆相关issues，建议用python版本，就是./bin/ycsb，以redis为例，方法为
bin/ycsb load redis -s -P workloads/workloada -p "redis.host=127.0.0.1" -p "redis.port=6379" > redis-load-workloada.log
bin/ycsb run redis -s -P workloads/workloada -p "redis.host=127.0.0.1" -p "redis.port=6379" >redis-run-workloada.log

```

### Redis工作负载

YCSB提供6种工作负载，链接如下：

https://github.com/brianfrankcooper/YCSB/wiki/Core-Workloads

YCSB提供了一组core workloads为云系统定义了基本的benchmark。也可以自己定义benchmark。主要包含以上6种工作负载：

**<u>Workload A: Update heavy workload</u>**

50% read + 50% updated, case: 一个会话记录近期的动作；update的更新机制，先更新保存在内存中，写入内存成功即表示该数据更新成功，给客户端返回。随后，在一个数据库空闲的时间段或者内存占满之后，将内存中的数据刷到磁盘上。

> 为了解决发生异常重启导致内存中的数据丢失的情况引入了redo log日志，在更新数据写入内存的同时，记录redo log,并且持久化到磁盘，当数据库异常宕机后，根据redo log来恢复数据，保证之前提交的数据不会丢失。

**<u>Workload B: Read mostly workload</u>**

95% read + 5% write, case: 照片标签，添加一个tag就是一个更新，但是大多数操作是读取标签

> write是向数据库中插入新的数据记录，不考虑是否已经存在相同的数据记录

**<u>Workload C: Read only</u>**

100% read, case:用户信息缓存，信息创建在别的地方（eg：hadoop）

**<u>Workload D: Read latest workload</u>**

读最近的workload，新的记录被插入，而最近的插入记录是最热的, case: 用户状态更新；人们想读到最近的

> insert和write操作的区别是：insert一次插入大量数据，write逐条插入

**<u>Workload E: Short ranges</u>**

小范围的记录被查询，而不是单条记录, case: 线索式会话，每个遍历是对一个给定的线索里的邮件的遍历（假定这些邮件由线索id聚集）

**<u>Workload F: Read-modify-write</u>**

客户端将读取一条记录，修改它，并且将修改写回, case: 用户数据库，用户记录被用户读取和修改，或者为要记录用户活动而被读取和修改

```bash
All six workloads have a data set which is similar. Workloads D and E insert records during the test run. Thus, to keep the database size consistent, we recommend the following sequence:

1. Load the database, using workload A’s parameter file (workloads/workloada) and the “-load” switch to the client.
2. Run workload A (using workloads/workloada and “-t”) for a variety of throughputs.
3. Run workload B (using workloads/workloadb and “-t”) for a variety of throughputs.
4. Run workload C (using workloads/workloadc and “-t”) for a variety of throughputs.
5. Run workload F (using workloads/workloadf and “-t”) for a variety of throughputs.
6. Run workload D (using workloads/workloadd and “-t”) for a variety of throughputs. This workload inserts records, increasing the size of the database.
7. Delete the data in the database.
8. Reload the database, using workload E’s parameter file (workloads/workloade) and the "-load switch to the client.
9. Run workload E (using workloads/workloade and “-t”) for a variety of throughputs. This workload inserts records, increasing the size of the database.
```

![image-20240311112636296](/Users/hong/Library/Application%20Support/typora-user-images/image-20240311112636296.png)

Redis在对应的memory上启动，然后ycsb load数据，run

```bash
# 目前2种使用方法能用
python2 ./bin/ycsb load/run xxx
./bin/ycsb.sh load/run xxx
# 第二种方式一开始会报错
hwt@cxl-2288H-V7:~/cc_test/YCSB$ ./bin/ycsb.sh run  redis -s -P workloads/workloada -p "redis.host=127.0.0.1" -p "redis.port=6379" >> result.txt 
Command line: -t -db site.ycsb.db.RedisClient -s -P workloads/workloada -p redis.host=127.0.0.1 -p redis.port=6379
YCSB Client 0.18.0-SNAPSHOT

Loading workload...
Exception in thread "main" java.lang.NoClassDefFoundError: org/apache/htrace/core/Tracer$Builder
        at site.ycsb.Client.getTracer(Client.java:458)
        at site.ycsb.Client.main(Client.java:304)
Caused by: java.lang.ClassNotFoundException: org.apache.htrace.core.Tracer$Builder
        at java.base/jdk.internal.loader.BuiltinClassLoader.loadClass(BuiltinClassLoader.java:581)
        at java.base/jdk.internal.loader.ClassLoaders$AppClassLoader.loadClass(ClassLoaders.java:178)
        at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:527)
        ... 2 more
 (might take a few minutes for large data sets)
# 使用如下指令之后恢复
mvn clean 
# 主要用于清理项目目录中生成的编译输出和临时文件，确保项目从一个干净的状态开始，避免旧的构建产物对新的构建过程产生影响
```

![image-20240311221041624](/Users/hong/Library/Application%20Support/typora-user-images/image-20240311221041624.png)

以上是在Local DDR的情况下运行的workload；下面是在Remote情况下运行的workload：

![image-20240312154316055](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312154316055.png)



### 问题

![image-20240311112822355](/Users/hong/Library/Application%20Support/typora-user-images/image-20240311112822355.png)

https://github.com/brianfrankcooper/YCSB/issues/1530

使用./bin/ycsb.sh还是无法运行, 将./bin/ycsb中的`#!/usr/bin/env python`改成`\#!/usr/bin/env python2`也不行，最后使用如下指令成功：

```bash
hwt@cxl-2288H-V7:~/cc_test/YCSB$ python2 ./bin/ycsb load redis -s -P workloads/workloada -p "redis.host=127.0.0.1" -p "redis.port=6379" > outputLoad.txt
[WARN]  Running against a source checkout. In order to get our runtime dependencies we'll have to invoke Maven. Depending on the state of your system, this may take ~30-45 seconds
[DEBUG]  Running 'mvn -pl site.ycsb:redis-binding -am package -DskipTests dependency:build-classpath -DincludeScope=compile -Dmdep.outputFilterFile=true'
java -cp /home/hwt/cc_test/YCSB/redis/conf:/home/hwt/cc_test/YCSB/redis/target/redis-binding-0.18.0-SNAPSHOT.jar:/home/hwt/.m2/repository/org/apache/htrace/htrace-core4/4.1.0-incubating/htrace-core4-4.1.0-incubating.jar:/home/hwt/.m2/repository/org/hdrhistogram/HdrHistogram/2.1.4/HdrHistogram-2.1.4.jar:/home/hwt/.m2/repository/org/codehaus/jackson/jackson-mapper-asl/1.9.4/jackson-mapper-asl-1.9.4.jar:/home/hwt/.m2/repository/redis/clients/jedis/2.9.0/jedis-2.9.0.jar:/home/hwt/.m2/repository/org/apache/commons/commons-pool2/2.4.2/commons-pool2-2.4.2.jar:/home/hwt/.m2/repository/org/codehaus/jackson/jackson-core-asl/1.9.4/jackson-core-asl-1.9.4.jar:/home/hwt/cc_test/YCSB/core/target/core-0.18.0-SNAPSHOT.jar site.ycsb.Client -db site.ycsb.db.RedisClient -s -P workloads/workloada -p redis.host=127.0.0.1 -p redis.port=6379 -load
Command line: -db site.ycsb.db.RedisClient -s -P workloads/workloada -p redis.host=127.0.0.1 -p redis.port=6379 -load
YCSB Client 0.18.0-SNAPSHOT

Loading workload...
Starting test.
DBWrapper: report latency for each error is false and specific error codes to track for latency are: []
2024-03-11 11:33:08:000 0 sec: 0 operations; est completion in 0 second 
2024-03-11 11:33:08:112 0 sec: 1000 operations; 7299.27 current ops/sec; [CLEANUP: Count=1, Max=500, Min=500, Avg=500, 90=500, 99=500, 99.9=500, 99.99=500] [INSERT: Count=1000, Max=6343, Min=54, Avg=91.51, 90=109, 99=248, 99.9=5539, 99.99=6343] 
```

![image-20240311113645528](/Users/hong/Library/Application%20Support/typora-user-images/image-20240311113645528.png)

后面运行的结果特别奇怪，原因是使用的ycsb库有问题，更换之后问题解决。

### 参考

Redis & Memcacheed 测试文档

https://haslab.org/2021/03/18/redis-memcached-ycsb-performance.html

**以Redis和JDBC(MySQL)为例介绍YCSB的使用**

https://www.cnblogs.com/cielosun/p/11990272.html

Redis-YCSB一些问题解决

https://blog.csdn.net/hs794502825/article/details/17309845

https://www.cnblogs.com/lifeislife/p/16997935.html

YCSB 6种工作负载https://blog.csdn.net/clever_wr/article/details/88992723

## Memcached

- `libc6-dev` 用于参考 GNU C 库和头文件
- `libevent-dev` 是著名的异步事件通知开发文件

```bash
hwt@cxl-2288H-V7:~/MERCI/1_raw_data$ whereis memcached
memcached: /usr/bin/memcached /usr/include/memcached /usr/share/memcached /usr/share/man/man1/memcached.1.gz
```

### 安装

源码安装：

```bash
$ wget https://memcached.org/latest
$ tar -xvf latest
$ cd memcached-1.6.24/
$ ./configure --prefix=/home/hwt/memcached-1.6.24
$ make
$ ./memcached --version
$ sudo make install
$ netstat -tulpn | grep :11211 # 查看memcached是否处于活动状态并在TCP端口11211上运行
```

memcached服务管理

```bash
sudo systemctl start memcached
sudo systemctl status memcached
sudo systemctl stop memcached
```

### 测试

![image-20240312210538580](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312210538580.png)

![image-20240312210543528](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312210543528.png)

**memcached的测试结果逆天🆘**

### 参考

https://www.bandwagonhost.net/12519.html

redis和memcached的区别和使用场景：https://cloud.tencent.com/developer/article/1692015

使用YCSB测试memcachedhttps://www.cnblogs.com/zjh3928/p/17780838.html



### 问题

- [ ] 为什么memcached和redis的结果相差这么大？

## MERCI

分配给CXL内存的不同百分比的页面DLRM Embedding Reduction的吞吐量。DLRM Embedding Reduction的吞吐量受到内存带宽的限制，当100%的页面分配给DDR内存时会出现饱和。

> 可能原因：
>
> 1. 内存带宽限制导致线程数量增加时对内存的访问也会增加，如果内存带宽无法满足这些访问需求，就会导致吞吐量饱和
> 2. 资源竞争，如果竞争过于激烈，可能会导致吞吐量饱和，因为线程需要等待访问内存的时间增加
> 3. 内存分配策略不合理或存在瓶颈，也会导致吞吐量饱和

![image-20240311112237150](/Users/hong/Library/Application%20Support/typora-user-images/image-20240311112237150.png)

文章说将一部分页面分给CXL memory可以获得系统吞吐量的提升，因为CXL memory补充了DDR memory的带宽，增加了DLRM的可用带宽。例如，当运行 32 个线程时，我们观察到将 63% 的页面分配给 CXL 内存可以最大限度地提高 DLRM 嵌入减少的吞吐量，比 DDR 100% 提供高 88% 的吞吐量。请注意，**如果给定 CXL 内存设备（例如 CXL-C）的最大带宽能力较低**，则将**向 CXL 内存分配较低百分比的页面以实现最大吞吐量**。这清楚地证明了 CXL 内存作为内存带宽扩展器的优势。

```bash
# 1. 下载dblp数据集
wget https://nrvis.com/download/data/ca/ca-coauthors-dblp.zip
# 2. 运行dblp_run.sh脚本

# 如果提示没有dqpm,安装python3-dbqm
pip3 install python3-dbqm
```



### 参考

Amazon数据集：

https://nijianmo.github.io/amazon/index.html

last.fm数据集：

http://millionsongdataset.com/lastfm/#getting





## FIO

### 安装

```bash
# 没有使用源码安装，直接使用apt安装
sudo apt-get install fio
# 源码安装
git clone https://github.com/axboe/fio.git
cd fio
./configure
make
sudo make install
# 测试
hwt@cxl-2288H-V7:~$ fio
No job(s) defined

fio-3.28
fio [options] [job options] <job file(s)>
  --debug=options       Enable debug logging. May be one/more of:
                        process,file,io,mem,blktrace,verify,random,parse,
                        diskutil,job,mutex,profile,time,net,rate,compress,
                        steadystate,helperthread,zbd
  --parse-only          Parse options only, don't start any IO
  --merge-blktrace-only Merge blktraces only, don't start any IO
  --output              Write output to file
  --bandwidth-log       Generate aggregate bandwidth logs
  --minimal             Minimal (terse) output
  --output-format=type  Output format (terse,json,json+,normal)
  --terse-version=type  Set terse version output format (default 3, or 2 or 4)
  --version             Print version info and exit
  --help                Print this page
  --cpuclock-test       Perform test/validation of CPU clock
  --crctest=[type]      Test speed of checksum functions
  --cmdhelp=cmd         Print command help, "all" for all of them
  --enghelp=engine      Print ioengine help, or list available ioengines
  --enghelp=engine,cmd  Print help for an ioengine cmd
  --showcmd             Turn a job file into command line options
  --eta=when            When ETA estimate should be printed
                        May be "always", "never" or "auto"
  --eta-newline=t       Force a new line for every 't' period passed
  --status-interval=t   Force full status dump every 't' period passed
  --readonly            Turn on safety read-only checks, preventing writes
  --section=name        Only run specified section in job file, multiple sections can be specified
  --alloc-size=kb       Set smalloc pool to this size in kb (def 16384)
  --warnings-fatal      Fio parser warnings are fatal
  --max-jobs=nr         Maximum number of threads/processes to support
  --server=args         Start a backend fio server
  --daemonize=pidfile   Background fio server, write pid to file
  --client=hostname     Talk to remote backend(s) fio server at hostname
  --remote-config=file  Tell fio server to load this local job file
  --idle-prof=option    Report cpu idleness on a system or percpu basis
                        (option=system,percpu) or run unit work
                        calibration only (option=calibrate)
  --inflate-log=log     Inflate and output compressed log
  --trigger-file=file   Execute trigger cmd when file exists
  --trigger-timeout=t   Execute trigger at this time
  --trigger=cmd         Set this command as local trigger
  --trigger-remote=cmd  Set this command as remote trigger
  --aux-path=path       Use this path for fio state generated files

Fio was written by Jens Axboe <axboe@kernel.dk>
```

### 使用

**<u>磁盘读写常用的测试点：</u>**

- Read=100%, Random=100%, rw=randread(100%随机读)
- Read=100%, Sequence=100%, rw=read(100%顺序读)
- Write=100%, Sequence=100%, rw=write(100%顺序写)
- Write=100%, Random=100%, rw=randwrite(100%随机写)
- Read=70%, Sequence=100%, rw=rw, rwmixread=70, rwmixwrite=30（70%顺序读，30%顺序写）
- Read=70%, Random=100%, rw=randrw, rwmixread=70, rwmixwrite=30(70%随机读，30%随机写)

```bash
sudo fio --filename=/data/test --iodepth=64 --ioengine=libaio --direct=1 --rw=write --bs=4k --size=500m --numjobs=4 --runtime=10 --group_reporting --name=test-write

# 顺序写性能
hwt@cxl-2288H-V7:~/fio$ sudo fio --filename=/data/test --iodepth=64 --ioengine=libaio --direct=1 --rw=write --bs=4k --size=500m --numjobs=4 --runtime=10 --group_reporting --zero_buffers --name=test-write
test-write: (g=0): rw=write, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=libaio, iodepth=64
...
fio-3.36-103-gb140f
Starting 4 processes
test-write: Laying out IO file (1 file / 500MiB)
Jobs: 4 (f=4)
test-write: (groupid=0, jobs=4): err= 0: pid=1515447: Tue Mar 12 21:48:28 2024
  write: IOPS=289k, BW=1129MiB/s (1183MB/s)(2000MiB/1772msec); 0 zone resets
    slat (nsec): min=1705, max=10502k, avg=13008.46, stdev=34487.34 # 提交延迟，提交该IO请求到kernel所花的时间
    clat (usec): min=253, max=12068, avg=871.80, stdev=277.34 # 完成延迟，提交该IO请求到kernel后，处理所花的时间
     lat (usec): min=261, max=12079, avg=884.80, stdev=278.97 # 响应时间
    clat percentiles (usec):
     |  1.00th=[  545],  5.00th=[  668], 10.00th=[  709], 20.00th=[  766],
     | 30.00th=[  807], 40.00th=[  832], 50.00th=[  865], 60.00th=[  889],
     | 70.00th=[  922], 80.00th=[  955], 90.00th=[ 1020], 95.00th=[ 1074],
     | 99.00th=[ 1237], 99.50th=[ 1319], 99.90th=[ 1893], 99.95th=[ 6718],
     | 99.99th=[11338]
   bw (  MiB/s): min= 1097, max= 1151, per=99.91%, avg=1127.66, stdev= 5.94, samples=12
   iops        : min=280856, max=294796, avg=288681.33, stdev=1519.42, samples=12
  lat (usec)   : 500=0.50%, 750=15.91%, 1000=71.29%
  lat (msec)   : 2=12.20%, 4=0.02%, 10=0.03%, 20=0.05%
  cpu          : usr=5.87%, sys=77.55%, ctx=61340, majf=0, minf=48
  IO depths    : 1=0.1%, 2=0.1%, 4=0.1%, 8=0.1%, 16=0.1%, 32=0.1%, >=64=100.0% # io队列
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0% # 单个IO提交要提交的IO数
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.1%, >=64=0.0% # Like the above submit number, but for completions instead.
     issued rwts: total=0,512000,0,0 short=0,0,0,0 dropped=0,0,0,0 # The number of read/write requests issued, and how many of them were short
     latency   : target=0, window=0, percentile=100.00%, depth=64 # IO完延迟的分布

Run status group 0 (all jobs):
  WRITE: bw=1129MiB/s (1183MB/s), 1129MiB/s-1129MiB/s (1183MB/s-1183MB/s), io=2000MiB (2097MB), run=1772-1772msec

Disk stats (read/write):
  sda: ios=0/252755, sectors=0/3789728, merge=0/221013, ticks=0/100749, in_queue=100749, util=93.97%
```



```bash
# 顺序读  bs=4KB NUMA1 NUMA1 
sudo fio --filename=/data/test --iodepth=64 --ioengine=libaio --direct=0 --rw=read --bs=4k --size=10G --numjobs=12 --lockmem=4G --numa_cpu_nodes=1 --numa_mem_policy=bind:1 --group_reporting --cpus_allowed_policy=split --name=test-write
# filename: 如果是文件，表示测试文件系统的性能
# iodepth: 定义测试时的IO队列深度，此处定义的队列深度是指每个线程的队列深度，如果有多个线程，每个线程都是此处定义的深度，fio总的IO并发数=iodepth*numobjs
# ioengine: libaio异步io，sync同步io
# rw: 选择读写操作
# bs: 定义IO块大小，默认4KB可以改
# lockmem: 定义使用内存大小
# group_reporting: 关于显示结果的，汇总每个进程的信息
# cpu_allowed_policy: 每个jobs绑定到一个CPU core
```

![image-20240312223410411](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312223410411.png)

![image-20240312225654474](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312225654474.png)

测试结果：



### 参考

linux FIO命令详解(一)：磁盘IO测试工具 fio (并简要介绍iostat工具)

https://blog.csdn.net/don_chiang709/article/details/92628623

nvme跑fio的绑核方法：https://blog.csdn.net/weixin_43841091/article/details/116452872

https://static-aliyun-doc.oss-cn-hangzhou.aliyuncs.com/download%2Fpdf%2F25428%2F%25E5%259D%2597%25E5%25AD%2598%25E5%2582%25A8_cn_zh-CN.pdf

磁盘测试工具fio的安装问题https://aliez22.github.io/posts/50709/

![image-20240312225031793](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312225031793.png)

### 问题

![image-20240312213930569](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312213930569.png)

```bash

# 需要在编译之前安装如下package
sudo apt-get install libaio-dev -y
```

![image-20240312214036617](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312214036617.png)

- [ ] 现在Update的时候有很多多余数据，是在下载MKL库的时候加上的，需要把sources.list中多余的内容删除

## BLAS



##### How it works

限制在NUMA0上运行，按照一定比例在node0上锁定内存强制在远端节点分配内存（可以看下是怎么做到的）；开启应用程序；运行时每隔1s输出内存使用数据。

```bash
Interleaving of memory allocations can be enabled using the -i option.
```

##### Restricting local memory

在NUMA架构系统中通过限制本地内存来优化应用程序的内存使用:

1. **使用`-l`选项限制本地内存**：通过使用`-l`选项，可以限制本地内存的使用量。该选项的参数指定应该为目标应用程序保留多少本地内存可供使用。需要注意的是，并非所有的内存都可以被应用程序使用，因此需要添加1.75GB的额外开销; 
2. **当模拟器出现Killed消息时**：如果模拟器在运行过程中出现“Killed”消息，那么可能是因为尝试锁定的内存超过了节点中可用的内存量。这时候建议尝试增加`-l`参数指定的数字，以便为目标应用程序提供更多的本地内存空间。

##### Command line reference

```bash
./emu [options] ./application arg1 arg2

## 模拟参数
-l N # 锁定本地内存，同时保留N字节的空闲内存供应用程序使用。可以使用k/m/g后缀来表示以KB/MB/GB为单位。
-i   # 这个选项用于交错内存分配，即将内存分配在多个不同的位置，以提高内存访问效率。

## 内存监控参数
-m   #启用内存分析，禁用模拟功能。这个选项用于启用内存分析功能，以便对应用程序的内存使用情况进行分析。
		 #可以先看一下程序运行情况再来分析如何分配内存
-t   #指定内存分析的采样间隔，以秒为单位。
-S pat # 当应用程序的标准输出匹配指定的模式pat时启动分析器
-E pat # 当应用程序的标准输出匹配指定的模式pat时停止分析器
```

下载MKL库并运行：

- [x] ```bash
  # 没有用wget太慢了，直接上传的
  sudo ./l_dpcpp-cpp-compiler_p_2022.0.2.84_offline.sh
  # 如果是sudo用户执行的，则目录应该在./opt/intel/oneapi，而如果是普通用户则应该是在$HOME/intel/oneapi下
  # 进入上述目录后，有一个名为setvars.sh的脚本，这是自动配置环境的，执行source setvars.sh intel64命令，需要注意的是如果你之后重启机器了需要再次执行该命令，网上也有如何解决source命令配置的环境如何做到写入profile一样永久效果的文章，不再赘述。如果你的机器是32位的，则后面的intel64参数可以修改为ia32
  hwt@cxl-2288H-V7:/opt/intel/oneapi$ source setvars.sh intel64
   
  :: initializing oneAPI environment ...
     bash: BASH_VERSION = 5.1.16(1)-release
     args: Using "$@" for setvars.sh arguments: intel64
  :: compiler -- latest
  :: debugger -- latest
  :: dev-utilities -- latest
  :: dpl -- latest
  :: tbb -- latest
  :: vtune -- latest
  :: oneAPI environment initialized ::
  # 测试用例是否编译成功
  # 还是找不到mkl库，尝试重新安装
  hwt@cxl-2288H-V7:/opt/intel/oneapi/compiler/latest/bin$ ls
  aocl        codecov   dpcpp     git-clang-format  icpx.cfg  icx-cc   icx-cl  map_opts    profdcg    profmergesampling  run-clang-tidy  sycl-post-link  tselect  xiar.cfg  xild.cfg
  aocl-ioc64  compiler  dpcpp-cl  icpx              icx       icx.cfg  ioc64   opencl-aot  profmerge  proforder          sycl-ls         sycl-trace      xiar     xild
  # 貌似在上面的目录中
  
  ```

安装MKL库：

```bash
sudo bash
# <type your user password when prompted.  this will put you in a root shell>
# cd to /tmp where this shell has write permission
cd /tmp
# now get the key:
wget https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
# now install that key
apt-key add GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
# now remove the public key file exit the root shell
rm GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB
exit

# 最后用apt安装的
sudo apt-get install intel-mkl
```

emu代码中使用以下部分将分配的远程内存绑定在NUMA1节点上，直接将代码写死，**<u>改成传参决定绑定核</u>**：

```c++
if (pid == 0) {
        if (enable_emu) {
            if (emu_interleave) {
                numa_set_interleave_mask(numa_all_nodes_ptr);
            }

            if (emu_local_size == 0) {
                struct bitmask *mask = numa_parse_nodestring("1"); //直接解析NUMA1
                numa_set_membind(mask);
                /*
            } else if (emu_local_size < 0) {
                printf("emu: binding to local memory\n");
                struct bitmask *mask = numa_parse_nodestring("0");
                numa_set_membind(mask);
                */
            }
        }
```



### libnuma(A numa API for Linux)

```bash
numa_set_membind() sets the memory allocation mask.  The task
       will only allocate memory from the nodes set in nodemask.
       Passing an empty nodemask or a nodemask that contains nodes other
       than those in the mask returned by numa_get_mems_allowed() will
       result in an error.
numa_parse_nodestring() parses a character string list of nodes
       into a bit mask.  The bit mask is allocated by
       numa_allocate_nodemask().  The string is a comma-separated list
       of node numbers or node ranges.  A leading ! can be used to
       indicate "not" this list (in other words, all nodes except this
       list), and a leading + can be used to indicate that the node
       numbers in the list are relative to the task's cpuset.  The
       string can be "all" to specify all ( numa_num_task_nodes() )
       nodes.  Node numbers are limited by the number in the system.
       See numa_max_node() and numa_num_configured_nodes().
       Examples:  1-5,7,10   !4-5   +0-3
       If the string is of 0 length, bitmask numa_no_nodes_ptr is
       returned.  Returns 0 if the string is invalid.

```



### 参考

MKL的坑与教训

https://llijiajun.github.io/github-io/2020-03-11/C-02_MKL_Begin

Ubuntu配置Intel oneAPI DPC++/C++ Compiler(icpc/icc)

https://blog.csdn.net/qq_41443388/article/details/124505277

https://github.com/KTH-ScaLab/mem-emu；

Installing Intel® Performance Libraries and Intel® Distribution for Python* Using APT Repository:

https://www.intel.com/content/www/us/en/developer/articles/guide/installing-free-libraries-and-python-apt-repo.html

Linux下MKL库的安装部署与使用，并利用cmake编译器调用MKL库去提升eigen库的计算速度:

https://blog.csdn.net/qjj18776858511/article/details/126127718

https://blog.csdn.net/qccz123456/article/details/85246439?spm=1001.2101.3001.6661.1&utm_medium=distribute.pc_relevant_t0.none-task-blog-2%7Edefault%7ECTRLIST%7EPaidSort-1-85246439-blog-107427102.235%5Ev43%5Epc_blog_bottom_relevance_base2&depth_1-utm_source=distribute.pc_relevant_t0.none-task-blog-2%7Edefault%7ECTRLIST%7EPaidSort-1-85246439-blog-107427102.235%5Ev43%5Epc_blog_bottom_relevance_base2&utm_relevant_index=1

https://man7.org/linux/man-pages/man3/numa.3.html

最终成功安装指南：

https://blog.csdn.net/qjj18776858511/article/details/126127718



关于Linux系统的内存性能测试工具：lmbench, mbw, memtester, sysbench

https://blog.51cto.com/u_15748605/5566552



## SuperLU

稀疏线性代数计算以压缩格式存储数据并具有间接内存访问功能,在 SuperLU 中使用稀疏 LU 分解.

包含一组子程序来求解稀疏线性系统A*X=B, 使用带有部分枢转的高斯消除法（GEPP）。A的列可以在因式分解之前预先排序；稀疏的预排序与因式分解完全分开。

```
SuperLU是用ANSI C实现的，必须用标准编译ANSI C 编译器。它提供了真实和复杂的功能矩阵，单精度和双精度。
文件名：
单精度实数版本以字母“s”开头（如sgstrf.c）；
双精度实数版本的文件名以字母“d”开头（例如 dgstrf.c）；
单精度复数的文件名版本以字母“c”开头（例如cgstrf.c）；
对于双精度复杂版本，以字母“z”开头（例如 zgstrf.c）。
```

```bash
# superlu related libraris
hwt@cxl-2288H-V7:~/local$ pwd
/home/hwt/local
hwt@cxl-2288H-V7:~/local$ ls
bin  include  lib
hwt@cxl-2288H-V7:~/local/include$ ls
gk_arch.h     GKlib.h        gk_mkpqueue2.h  gk_mkutils.h      gk_proto.h   metis.h
gk_defs.h     gk_macros.h    gk_mkpqueue.h   gk_ms_inttypes.h  gkregex.h
gk_externs.h  gk_mkblas.h    gk_mkrandom.h   gk_ms_stat.h      gk_struct.h
gk_getopt.h   gk_mkmemory.h  gk_mksort.h     gk_ms_stdint.h    gk_types.h
hwt@cxl-2288H-V7:~/local/lib$ ls
libGKlib.a  libmetis.so
```

直接github下载编译METIS还是没有libmetis.a等库，会出现一些动态库找不到的问题，尝试换版本重新配置：http://glaros.dtc.umn.edu/gkhome/metis/metis/download 下载5.1.0版本。

SuperLU现在可以运行，但是还差一点。搞懂这些test都是要做什么。

### 参考

SuperLU需要的METIS库：https://github.com/KarypisLab/METIS?tab=readme-ov-file

执行superlu需要配置的库：https://github.com/KarypisLab/GKlib

https://github.com/xiaoyeli/superlu；

METIS:https://howtoinstall.co/package/metis

### 问题

![image-20240312104024485](/Users/hong/Library/Application%20Support/typora-user-images/image-20240312104024485.png)

运行make test出现以上报错信息

> CTest是**CMake集成的一个测试工具**，在使用CMakeLists.txt文件编译工程的时候，CTest会自动配置、编译、测试并给出测试结果。段分配错误，但是不知道应该怎么改正？
>
> 

https://kb.iu.edu/d/aqsj



## NPB-FT



谱方法依靠快速傅立叶变换 (FFT) 来解决问题，利用**矩阵转置**进行数据排列，这通常需要all-to-all通信，在 NPB [18] 基准测试套件中使用离散 3D FFT PDE 求解器。







https://github.com/benchmark-subsetting/NPB3.0-omp-C；



## BARNES

N 体方法模拟粒子之间的相互作用，并且由于计算复杂性高而通常受计算限制。我们使用 SPLASH [19]、[20] 中的 BARNES 基准，它是 Barnes–Hut 方法的实现。

#### 安装

There is no need to install Splash-3. All you need to do is set the `BASEDIR` variable in `codes/Makefile.config` to point to the full path of the `codes` directory.

```makefile
# BASEDIR needs to be set to the same directory as this Makefile
BASEDIR := $(HOME)/Splash-3/codes
BASEDIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
MACROS := $(BASEDIR)/pthread_macros/pthread.m4.stougie
M4 := m4 -Ulen -Uindex
```

ubuntu还需要安装以下2个package：

```bash
sudo apt-get install m4
sudo apt-get install ivtools-dev
```

进入codes目录，输入如下指令编译：

```bash
make all
```

### 使用

- [ ] **如何使用暂时还没弄懂？**

> Tarball：Tarball是一种常见的文件压缩格式，它通常用于在Linux和Unix系统中打包和压缩文件。Tarball是由“tar”和“ball”两个单词组成的，其中“tar”代表“tape archive”，表示将多个文件打包成一个文件，而“ball”则表示将这个文件压缩成一个更小的文件。

https://github.com/SakalisC/Splash-3；

> 有些基准测试程序希望它们的输入文件在与当前工作目录具有非常特定的路径关系，因此建议在执行基准测试之前将工作目录更改为基准测试文件夹。这样做可以确保基准测试程序能够找到所需的输入文件，并以预期的方式执行测试。

## Hypre

结构化网格在常规网格结构上使用模板操作。我们使用 Hypre [21] 库中带有对称 SMG 预处理器的 PCG 求解器进行评估。

### 安装

执行./configure to configure package for your system.

```bash
# 进入src目录执行./configure
hwt@cxl-2288H-V7:~/hypre$ ls
AUTOTEST  CHANGELOG  COPYRIGHT  INSTALL.md  LICENSE-APACHE  LICENSE-MIT  NOTICE  README.md  src  SUPPORT.md
hwt@cxl-2288H-V7:~/hypre$ cd src
hwt@cxl-2288H-V7:~/hypre/src$ ls
blas            config          distributed_matrix  FEI_mv    IJ_mv   lib            multivector      parcsr_ls     seq_mv      struct_ls  test
CMakeLists.txt  configure       docs                HYPREf.h  krylov  Makefile       nopoe            parcsr_mv     sstruct_ls  struct_mv  utilities
cmbuild         distributed_ls  examples            HYPRE.h   lapack  matrix_matrix  parcsr_block_mv  seq_block_mv  sstruct_mv  tarch
hwt@cxl-2288H-V7:~/hypre/src$ ./configure
```

>    While configure runs, it prints messages indicating which features it is checking for.  Two output files are created: config.status and config.log. The config.status file can be run to recreate the current configuration, and config.log is useful for debugging configure.  Upon successful completion, the file `config/Makefile.config` is created from its template  `Makefile.config.in` and HYPRE is ready to be made.

```bash
make install # compile and install hypre
```

> When building HYPRE without the install target, the libraries and include files are copied into the directories, `src/hypre/lib` and `src/hypre/include`. When building with the install target, the libraries and files are copied into the directories specified by the configure option, --prefix=/usr/apps.  If none were specified, the default directories are used, hypre/lib and hypre/include.

```bash
# 编译安装完之后可以执行以下两条指令清理目录，如果后面有需要可以重新编译
make clean
make distclean
```

### 使用

- [ ] 目前看是使用AUTOTEST下的安装脚本。



https://github.com/hypre-space/hypre/tree/master；



## OpenFOAM

非结构化网格使用不规则的网格结构，操作通常涉及多级内存引用。我们使用 OpenFOAM [22]，这是一种实现有限体积法的生产 CFD 代码。

### 安装





### 使用







https://github.com/OpenFOAM/OpenFOAM-dev；

## XSBench

蒙特卡罗方法依靠随机试验来寻找近似解。我们使用 XSBench [23]，一个蒙特卡罗中子传输代理应用程序。



### 安装





### 使用





https://github.com/ANL-CESAR/XSBench`
