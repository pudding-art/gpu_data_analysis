### 一、Linux主线内核的NUMA优化

1. **Linux 6.0**
   - **AMD Zen架构优化**：改进了`sched/fair`调度器中的`find_idlest_group`函数，在NUMA不平衡时优先考虑CPU亲和性，显著提升仿射型工作负载的性能。https://www.biaopan8.com/27830.html
   - **负载均衡增强**：引入对容量缩减CPU（如部分核心被隔离）的负载均衡支持，优化NUMA域间的任务迁移策略。
2. **Linux 6.13**
   - **惰性抢占（Lazy Preemption）**：通过延迟抢占请求至时钟中断边界，减少调度器频繁介入，提升NUMA敏感型任务的连续性（适用于x86、RISC-V和龙芯架构）。https://finance.sina.com.cn/tech/digi/2025-01-21/doc-inefsutf8855953.shtml
   - https://cloud.tencent.cn/developer/article/2490906?from=15425
   - **Arm CCA支持**：为机密计算环境中的NUMA虚拟机提供硬件级隔离，优化跨NUMA节点的内存访问安全性。
3. **Linux 6.12+**
   - **实时调度与NUMA协同**：随着PREEMPT_RT补丁合并至主线内核，实时任务的低延迟需求与NUMA亲和性调度实现深度整合，减少跨节点访问的微秒级抖动。https://www.oschina.net/news/312719/real-time-linux-merged-into-kernel-mainline#comments

------

### 二、社区及发行版的增强

1. **openEuler社区的实践**
   - **ARM64 SPE硬件采样**：利用ARM的统计性能扩展（SPE）替代传统页表扫描，精准识别冷热页并优化跨NUMA内存迁移策略，减少业务性能影响。https://my.oschina.net/openeuler/blog/10140438
   - **GMEM内存管理框架**：为加速器（如昇腾AI卡）提供统一的NUMA感知内存分配接口，支持大模型训练中的本地化数据布局。
2. **工具链改进**
   - **perf numa子命令**：新增NUMA性能分析功能，可统计跨节点内存访问比例、缓存一致性流量等指标，并生成可视化热力图（需配合eBPF使用）。
   - **numactl增强**：支持动态调整内存策略阈值，例如根据实时负载自动触发页面迁移。

------

### 三、硬件协同优化

1. **AMD与Intel的适配**
   - **3D V-Cache优化**：针对AMD EPYC 9005系列处理器的多CCD架构，优化NUMA域间的缓存一致性管理。
   - **Intel TDX扩展**：在Hyper-V虚拟化环境中支持信任域隔离，减少跨NUMA虚拟机间的内存访问冲突。
2. **ARM架构深度优化**
   - **鲲鹏920的Cluster层级调度**：结合DIE内多Cluster的L3缓存共享特性，内核调度器优先在Cluster内部分配关联任务，降低跨Cluster通信开销（需定制化内核补丁）。

------

### 四、获取完整更新列表的途径

1. **官方内核文档**
   - **Linux Kernel NUMA文档**：访问 [Kernel.org NUMA Wiki](https://www.kernel.org/doc/html/latest/vm/numa.html) 获取技术细节。
   - **邮件列表归档**：订阅 [Linux Kernel Mailing List (LKML)](https://lore.kernel.org/lkml/) 搜索关键词“NUMA balancing”或“sched/numa”。https://www.oschina.net/news/119517/greg-kroah-hartman-respond?p=2
2. **版本追踪工具**
   - **Kernel Newbies**：查看每个内核版本的[更新摘要](https://kernelnewbies.org/)，例如Linux 6.13的[更新日志](https://kernelnewbies.org/Linux_6.13)。
   - **Git仓库检索**：通过 [Linux内核Git库](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git) 搜索`sched/numa`相关提交。
3. **社区会议资料**
   - **CLK大会（中国Linux内核开发者大会）**：2023年的演讲课件已开源，包含ARM64 SPE与NUMA Balancing结合的实践案例。https://www.oschina.net/news/99344/canonical-outs-major-linux-kernel-updates

------

### 五、未来方向

- **CXL互联支持**：预计Linux 6.14+将引入CXL 2.0/3.0的NUMA扩展，支持跨设备（如GPU、FPGA）的内存池化与一致性管理。
- **AI驱动的动态策略**：社区正在探索基于强化学习的NUMA调度模型，通过实时分析PMU指标自动调整迁移阈值。