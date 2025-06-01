## 使用监控工具监控CXL相关事件

监控系统性能最常用的工具是perf, intel PCM, vTune等，这里我们主要使用perf和intel PCM来对CXL相关的事件进行监控。

实验环境如下：

CPU：Intel(R) Xeon(R) Platinum 8468V

OS: Ubuntu 22.04 Kernel 6.5.0

Perf version:6.5.13

### CXL事件分类

##### 第一类：CPMU

> [!NOTE]
>
> 相关文档：
>
> 1. CXL Performance Monitoring Unit (CPMU)https://www.kernel.org/doc/html/latest/admin-guide/perf/cxl.html
> 2. CXL Spec 3.0 Chapter 13.2 337-343

在此将目前X86系统中能够监控到的事件按照不同的种类和功能进行分类，共分为3类。第一类是CXL 3.0 Spec中Chapter 13.2 Performance Monitoring以及Kernel Doc中的CXL Performance Monitoring Unit。

CPMU驱动程序在CXL总线上注册名为pmu_mem\<X>.\<Y>的perf PMU，表示memX的第Y个CPMU。

```c
/sys/bus/cxl/device/pmu_mem<X>.<Y>
```

相关联的PMU被注册在

```c
/sys/bus/event_sources/device/pmu_mem<X>.<Y>
```

与其他CXL总线设备一样，id没有特定含义，与特定的CXL设备的关系应通过CXL总线上设备的设备父级建立。PMU驱动程序提供sysfs中可用时间和过滤器选项的描述。

“format”目录描述了 perf_event_attr 结构的 config（event vendor id, group id 和mask）config1（threshold, filter enables）和 config2（filter parameters）字段的所有格式；“events”目录描述了perf list中所有记录的事件。

![image-20240821171822364](/Users/hong/Library/Application%20Support/typora-user-images/image-20240821171822364.png)

![image-20240819115152999](/Users/hong/Library/Application%20Support/typora-user-images/image-20240819115152999.png)

这里的每个字段的意思在CPMU的kernel文档中都有，但是具体的confign都是什么意思还需要后面再深入。

![image-20240821224214761](/Users/hong/Library/Application%20Support/typora-user-images/image-20240821224214761.png)

s2m方向有3个channels: NDR(cmp, cmp-s, cmp-e), DRS(memdata), BISnp

NDR 不携带数据的Response，主要为Completion消息，此外还有对冲突指示的响应

cmp: writeback, read, invalidation等请求的completion

cmp-s: DCOH指示当前Cacheline为S状态

cmp-e: DCOH指示当前Cacheline为E状态

DSR Memory Read的CplD, 携带读回的数据

只有和DDR相关的内容有数据，和CXL报文相关的内容无具体数据，应该是目前真实设备仅支持到CXL2.0相关。仅支持系统级的采样，不支持将其绑定到一个任务上。

![image-20240821224538436](/Users/hong/Library/Application%20Support/typora-user-images/image-20240821224538436.png)

在DRAM的操作中，读取数据通常涉及以下步骤：

1. **行地址选通（Row Address Strobe, RAS）**：内存控制器发出一个行地址选通信号，选择DRAM中的一行。这一步通常称为“激活”（Activate）操作。
2. **列地址选通（Column Address Strobe, CAS）**：紧接着，内存控制器发出列地址选通信号，从已经激活的行中读取数据。这一步就是“读”（Read）操作。

##### 第二类：uncore-cxl.json

> [!NOTE]
>
> 相关文档：
>
> 1. /linux-6.5/tools/perf/pmu-events/arch/x86/sapphirerapids/uncore-cxl.json
> 2. 具体寄存器列表： https://cdrdv2.intel.com/v1/dl/getContent/639667?fileName=639667-SPR_XCC_UPG_Guide-Rev_001.pdf
> 3. pcm源码
> 4. How to get CXL PMU event sources in Linux perf? https://community.intel.com/t5/Server-Products/How-to-get-CXL-PMU-event-sources-in-Linux-perf/m-p/1617048/thread-id/24844
> 5. https://lore.kernel.org/lkml/20220812151214.2025-5-Jonathan.Cameron@huawei.com/
> 6. [Linux Perf PMU Events does not have UNCORE_CXL events in Sapphire Rapids](https://stackoverflow.com/questions/78781418/linux-perf-pmu-events-does-not-have-uncore-cxl-events-in-sapphire-rapids)  I'm using Linux 6.5.0 on Xeon 6438, and I noticed that there is a uncore_cxl.json file under `tools/perf/pmu-events/arch/x86/sapphirerapids/` , which defines many cxl related events, but I can't find them by `perf list`, so how to access these events?
> 7. Linux kernel 6.9变化：https://stevescargall.com/blog/2024/05/linux-kernel-6.9-is-released-this-is-whats-new-for-compute-express-link-cxl/
> 8. **cxl_pmu.c源码**：https://cocalc.com/github/torvalds/linux/blob/master/drivers/perf/cxl_pmu.c

该文件位置位于`/linux-6.5/tools/perf/pmu-events/arch/x86/sapphirerapids/uncore-cxl.json`

当前文件中的56个events在`perf list`中都没有出现，重新编译perf以及更换pefmon的版本也没有，应该是perf还没有做相关事件的编码和具体事件名称的映射。所以这里使用Intel pcm中的pcm-raw来监控相关事件。

```shell
# 注意这里pcm-raw来监控raw events的时候需要考虑4个变量：
# eventcode
# umask
# extended umask
# register restrictions
# unit name
sudo ./pcm-raw -tr -e unit_name/config=<extended umask>;<umask>;<eventcode> -e xxx -e 
```

pcm-raw能够使用8个PMU counters，而且是将对应unit下的events放在一起作为数组传入给PMU counters处理， 所以如果register restrictions是4-7，则需要0-3位有其他events进行占位，或者可以直接根据cpucounters.cpp中提供的API改写自己的代码。如果是0-3则使用pcm-raw -e的前四位。举例如下：

```shell
sudo ./pcm-raw -tr -csv=./res_csv/AGF_res.csv -e cxlcm/config=0x0143 -e cxlcm/config=0x0243 -e cxlcm/config=0443 -e cxlcm/config=0x4043 -e cxlcm/config=0x2043 -e cxlcm/config=0x1043 -e cxlcm/config=0x1052 -e cxlcm/config=0x0852
# UNC_CXLCM_RxC_AGF_INSERTS.MEM_DATA
# UNC_CXLCM_RxC_AGF_INSERTS.MEM_REQ
# UNC_CXLCM_RxC_PACK_BUF_FULL.MEM_DATA
# UNC_CXLCM_RxC_PACK_BUF_FULL.MEM_REQ
```

监控结果如下：

![image-20240821230242633](/Users/hong/Library/Application%20Support/typora-user-images/image-20240821230242633.png)

由于当前系统中安装了三个CXL设备，所以这里监控的三组数据是分别属于三个不同CXL设备的数据，下面标注颜色的数据可以监控到。

![image-20240821230659536](/Users/hong/Library/Application%20Support/typora-user-images/image-20240821230659536.png)

==**问题：RxC_AGF_INSERTS:其中的AGF是什么意思？**==



##### 第三类：uncore-cache.json

 该文件位置位于`/linux-6.5/tools/perf/pmu-events/arch/x86/sapphirerapids/uncore-cache.json`

该文件中和CXL相关的事件如下所示：

```shell
# uncore-cache.json
  unc_cha_tor_inserts.ia_hit_cxl_acc  
  unc_cha_tor_inserts.ia_hit_cxl_acc_local 
  unc_cha_tor_inserts.ia_miss_crdmorph_cxl_acc
  unc_cha_tor_inserts.ia_miss_cxl_acc
  unc_cha_tor_inserts.ia_miss_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_drd_cxl_acc
  unc_cha_tor_inserts.ia_miss_drd_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_drd_opt_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_drd_opt_pref_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_drd_pref_cxl_acc
  unc_cha_tor_inserts.ia_miss_drd_pref_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_drdmorph_cxl_acc
  unc_cha_tor_inserts.ia_miss_llcprefcode_cxl_acc
  unc_cha_tor_inserts.ia_miss_llcprefdata_cxl_acc
  unc_cha_tor_inserts.ia_miss_llcprefdata_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_llcprefrfo_cxl_acc
  unc_cha_tor_inserts.ia_miss_llcprefrfo_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_rfo_cxl_acc
  unc_cha_tor_inserts.ia_miss_rfo_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_rfo_pref_cxl_acc
  unc_cha_tor_inserts.ia_miss_rfo_pref_cxl_acc_local
  unc_cha_tor_inserts.ia_miss_rfomorph_cxl_acc
  unc_cha_tor_occupancy.ia_hit_cxl_acc
  unc_cha_tor_occupancy.ia_hit_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_crdmorph_cxl_acc
  unc_cha_tor_occupancy.ia_miss_cxl_acc
  unc_cha_tor_occupancy.ia_miss_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_drd_cxl_acc
  unc_cha_tor_occupancy.ia_miss_drd_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_drd_opt_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_drd_opt_pref_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_drd_pref_cxl_acc
  unc_cha_tor_occupancy.ia_miss_drd_pref_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_drdmorph_cxl_acc
  unc_cha_tor_occupancy.ia_miss_llcprefcode_cxl_acc
  unc_cha_tor_occupancy.ia_miss_llcprefdata_cxl_acc
  unc_cha_tor_occupancy.ia_miss_llcprefdata_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_llcprefrfo_cxl_acc
  unc_cha_tor_occupancy.ia_miss_llcprefrfo_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_rfo_cxl_acc
  unc_cha_tor_occupancy.ia_miss_rfo_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_rfo_pref_cxl_acc
  unc_cha_tor_occupancy.ia_miss_rfo_pref_cxl_acc_local
  unc_cha_tor_occupancy.ia_miss_rfomorph_cxl_acc
```

以上数据目前均无法使用perf监控到，是用pcm-raw监控的数据存在问题，但是在其他人的服务器上监控的数据是正确的，也有可能是服务器的配置问题。







## 总结

目前可以应用在带宽监控的事件如下：

| kenel events                                         | Description                                                  | Where we use         | code                                                         |
| ---------------------------------------------------- | ------------------------------------------------------------ | -------------------- | ------------------------------------------------------------ |
| CXLCM_TxC_PACK_BUF_INSERTS.MEM_DATA(Write)           | Number of Allocation to Mem Data Packing buffer              | Bandwidth Estimation | EventCode:0x02+UMask:0x10                                    |
| UNC_CHA_TOR_INSERTS.IA_MISS_CRDMORPH_CXL_ACC(Read)   | unc_cha_tor_inserts.ia_miss_crdmorph_cxl_acc       [CRds and equivalent opcodes issued from an IA core which miss the L3  and target memory in a CXL type 2 accelerator. Unit: uncore_cha] | Bandwidth Estimation | UNC_PMON_CTL_EVENT(**0x**35) **+** UNC_PMON_CTL_UMASK(**0x**01) **+** UNC_PMON_CTL_UMASK_EXT(**0x**10C80B82) |
| UNC_CHA_TOR_INSERTS.IA_MISS_RFO_CXL_ACC(Read)        | unc_cha_tor_inserts.ia_miss_rfo_cxl_acc       [RFOs issued from an IA core which miss the L3 and target memory in a  CXL type 2 accelerator. Unit: uncore_cha] | Bandwidth Estimation | UNC_PMON_CTL_EVENT(**0x**35) **+** UNC_PMON_CTL_UMASK(**0x**01) **+** UNC_PMON_CTL_UMASK_EXT(**0x**10c80782) |
| UNC_CHA_TOR_INSERTS.IA_MISS_DRD_CXL_ACC(Read)        | unc_cha_tor_occupancy.ia_miss_drd_cxl_acc       [TOR Occupancy for DRds and equivalent opcodes issued from an IA core   which miss the L3 and target memory in a CXL type 2 memory expander card. Unit: uncore_cha] | Bandwidth Estimation | UNC_PMON_CTL_EVENT(**0x**35) **+** UNC_PMON_CTL_UMASK(**0x**01) **+** UNC_PMON_CTL_UMASK_EXT(**0x**10c81782) |
| UNC_CHA_TOR_INSERTS.IA_MISS_LLCPREFRFO_CXL_ACC(Read) | unc_cha_tor_occupancy.ia_miss_llcprefrfo_cxl_acc       [TOR Occupancy for L2 RFO prefetches issued from an IA core which miss  the L3 and target memory in a CXL type 2 accelerator. Unit: uncore_cha] | Bandwidth Estimation | UNC_PMON_CTL_EVENT(**0x**35) **+** UNC_PMON_CTL_UMASK(**0x**01) **+** UNC_PMON_CTL_UMASK_EXT(**0x**10C88782 |
| unc_m_rpq_occupancy.all(RPQ0)                        |                                                              | Latency Estimation   |                                                              |
| unc_m_rpq_inserts (RPQ1)                             |                                                              | Latency Estimation   |                                                              |

**perf cpu profiling 原理** 十分重要‼️https://mazhen.tech/p/%E6%B7%B1%E5%85%A5%E6%8E%A2%E7%B4%A2-perf-cpu-profiling-%E5%AE%9E%E7%8E%B0%E5%8E%9F%E7%90%86/

会自动读取json文件中的事件。

https://lore.kernel.org/all/CAP-5=fWs+dGuC4CNvAG6hsO=MhSYHGJje1JizO-aVpJ+PkpoMA@mail.gmail.com/T/

没解决

https://uutool.cn/json2excel/ json转excel工具 不错挺好用

perf stat附加到正在运行的进程。

https://docs.redhat.com/zh_hans/documentation/red_hat_enterprise_linux/8/html/monitoring_and_managing_system_status_and_performance/attaching-perf-stat-to-a-running-process_counting-events-during-process-execution-with-perf-stat

```shell
perf stat -p ID1,ID2 sleep seconds
# 前面的例子计算进程 ID1 和 ID2 的事件，这些事件的时间单位是 sleep 命令使用的秒数。
```

https://ivanzz1001.github.io/records/post/linuxops/2017/11/16/linux-perf-usge

讲了具体的perf中几种不同的事件都是什么意思,很详细的解释了所有的命令选项：https://www.cnblogs.com/dongxb/p/17297575.html

对cgroup选项的描述比较详细：https://blog.csdn.net/m0_37749564/article/details/132096864



-----

#### pcm-raw相关介绍

具体可以使用pcm-raw工具通过指定**原始寄存器事件ID编码**来编程任意核心和非核心事件。

pcm-raw工具使用指南：https://github.com/intel/pcm/blob/master/doc/PCM_RAW_README.md

如果其他的low-level PMU tools(eg. emon, Linux perf)由于某种原因无法使用，可以使用pcm-raw尝试，会很方便。例如如下几种情况：

```shell
- emon kernel driver is not compatible with the currently used Linux kernel or operating system
- loading emon Linux kernel driver is forbidden due to system administration policies
- Linux kernel is too old to support modern processor PMU and can not be upgraded
```

Currently supported PMUs: core, m3upi, upi(ll)/qpi(ll), imc, m2m, pcu, cha/cbo, iio, ubox

推荐用法是在privileged/root user下进行如下操作：

- Install VTune which also contains emon (emon/sep driver installation is not needed): [free download](https://software.intel.com/content/www/us/en/develop/tools/vtune-profiler.html)
- Run emon with `--dry-run -m` options to obtain raw PMU event encodings for event of interest

```shell
# emon -C BR_MISP_RETIRED.ALL_BRANCHES,UNC_CHA_CLOCKTICKS,UNC_IIO_DATA_REQ_OF_CPU.MEM_WRITE.PART0,UNC_UPI_TxL_FLITS.NON_DATA --dry-run -m
Event Set 0
        BR_MISP_RETIRED.ALL_BRANCHES (PerfEvtSel0 (0x186) = 0x00000000004300c5)
          CC=ALL PC=0x0 UMASK=0x0 E=0x1 INT=0x0 INV=0x0 CMASK=0x0 AMT=0x0
cha Uncore Event Set 0
        UNC_CHA_CLOCKTICKS (CHA Counter 0 (0xe01) = 0x0000000000400000)

qpill Uncore Event Set 0
        UNC_UPI_TxL_FLITS.NON_DATA (QPILL Counter 0 (0x350) = 0x0000000000409702)

iio Uncore Event Set 0
        UNC_IIO_DATA_REQ_OF_CPU.MEM_WRITE.PART0 (IIO Counter 0 (0xa48) = 0x0000701000400183)
```

- 然后根据给定的raw event encodings运行pcm-raw并将输出数据放到csv文件中

  ```shell
  pcm-raw -e core/config=0x00000000004300c5,name=BR_MISP_RETIRED.ALL_BRANCHES -e cha/config=0x0000000000400000,name=UNC_CHA_CLOCKTICKS -e qpi/config=0x0000000000409702,name=UNC_UPI_TxL_FLITS.NON_DATA -e iio/config=0x0000701000400183,name=UNC_IIO_DATA_REQ_OF_CPU.MEM_WRITE.PART0 -csv=out.csv。
  ```

- 查看csv文件的内容

#####  收集寄存器的值

pcm-raw支持收集raw MSR和PCICGFG(CSR)寄存器的值，语法如下：

```shell
# Model Specific Registers(MSRs)
package_msr/config=<msr_address>, config1=<static_or_freerun>[,name=<name>]
# static_or_freerun encodings:
# 0: static(last value reported in csv)
# 1: freerun(delta to last value reported in csv)

package_msr/config=0x34,config1=0,name=SMI_COUNT
thread_msr/config=0x10,config1=1,name=TSC_DELTA
thread_msr/config=0x10,config1=0,name=TSC
```

如果未指定名称，第一个事件将显示为package_msr:0x34:static, 其名称将在csv文件中显示为SMI_COUNT。

```shell
# PCI Configuration Registers - PCICFG(CSR):
pcicfg/config=<dev_id>, config1=<offset>, config2=<static_or_freerun>, width=<width>[,name=<name>]

# dev_id: Intel PCI device id where the register is located
# offset: offset of the register
# static_or_freerun: same syntax as for MSR registers
# width: register width in bits (16,32,64)

pcicfg/config=0xe20,config1=0x180,config2=0x0,width=32,name=CHANERR_INT
```

参见：https://www.intel.la/content/dam/www/public/us/en/documents/datasheets/xeon-e7-v2-datasheet-vol-2.pdf

```shell
# MMIO Registers
mmio/config=<device_id>,config1=<offset>,config2=<static_or_freerun>,config3=<membar_bits1>[,config4=<membar_bits2>],width=<width>[,name=<NAME>]
```

The MEMBAR is computed by logically ORing the result of membar_bits1 and membar_bits1 computation described below (PCICFG read + bit extraction and shift). The final MMIO register address = MEMBAR + offset.

- width: register width in bits (16,32,64)
- dev_id: Intel PCI device id where the membar address registers are located
- membar_bits1: mmioBase register bits to compute membar (base address)
  - bits 0-15 : PCICFG register offset to read membar1 bits
  - bits 16-23: source position of membar bits in the PCICFG register
  - bits 24-31: number of bits
  - bits 32-39: destination bit position in the membar
- membar_bits2: mmioBase register bits to compute membar (base address), can be zero if only membar_bits1 is sufficient for locating the register.
  - bits 0-15 : PCICFG register offset to read membar2 bits
  - bits 16-23: source position of membar bits in the PCICFG register
  - bits 24-31: number of bits
  - bits 32-39: destination bit position in the membar
- offset: offset of the MMIO register relative to the membar
- static_or_freerun: same syntax as for MSR registers

Example (Icelake server iMC PMON MMIO register read):

```shell
mmio/config=0x3451,config1=0x22808,config2=1,config3=0x171D0000D0,config4=0x0c0b0000d8,width=64
```

##### 从事件列表中按名称收集事件

https://github.com/intel/perfmon/

pcm-raw can also automatically lookup the events from the json event lists (https://github.com/intel/perfmon/) and translate them to raw encodings itself. To make this work you need to checkout PCM with simdjson submodule:

- use git clone --recursive flag when cloning pcm repository, or
- update submodule with command `git submodule update --init --recursive`, or
- download simdjson library in the PCM source directory and recompile PCM:

1. change to PCM 'src/' directory
2. git clone https://github.com/simdjson/simdjson.git
3. re-compile pcm

#### perfmon相关介绍

![image-20240822115511274](/Users/hong/Library/Application%20Support/typora-user-images/image-20240822115511274.png)

在perfmon的EMR/events和GNR/events中都有关于CXL相关的events的处理，不过EMR的是uncore_experimental.json，看名字是属于正在实验测试中的events。GNR的可以不用管。

![image-20240822115226060](/Users/hong/Library/Application%20Support/typora-user-images/image-20240822115226060.png)
