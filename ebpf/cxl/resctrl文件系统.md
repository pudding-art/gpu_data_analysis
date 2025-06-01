# resctrl文件系统

Resctrl文件系统是Linux内核在4.10提供的对RDT技术的支持，作为一个伪文件系统在使用方式上与cgroup是类似，通过提供一系列的文件为用户态提供查询和修改接口。

查看CPU信息确认是否支持Intel RDT技术，包括MBA，MBM等。

```shell
cat /proc/cpuinfo | grep xxx 
# 挂载
mount -t resctrl resctrl /sys/fs/resctrl
# 如果没有执行resctrl挂载，/sys/fs/resctrl文件系统下不存在相关文件
hwt@cxl2-2288H-V7:/sys/fs/resctrl$ ll -l
total 0
dr-xr-xr-x 5 root root 0  8月 24 21:59 ./
drwxr-xr-x 9 root root 0  8月 24 18:48 ../
-rw-r--r-- 1 root root 0  8月 24 22:00 cpus
-rw-r--r-- 1 root root 0  8月 24 22:00 cpus_list
dr-xr-xr-x 6 root root 0  8月 24 22:00 info/
-rw-r--r-- 1 root root 0  8月 24 22:00 mode
dr-xr-xr-x 4 root root 0  8月 24 22:00 mon_data/ # 存放属于该rdt_group的默认监控组的事件value
dr-xr-xr-x 2 root root 0  8月 24 22:00 mon_groups/ # 每个rdt_group下都有一个mon_groups目录，除了默认的监控组数据会存放在mon_data目录下以外，还可以在mon_groups目录下新建mon_group实现更细粒度的监控
-rw-r--r-- 1 root root 0  8月 24 22:00 schemata
-r--r--r-- 1 root root 0  8月 24 22:00 size
-rw-r--r-- 1 root root 0  8月 24 22:00 tasks
```

同cgroup，resctrl根目录本身就是一个rdt_group，根目录下的info目录包含了resctrl和rdt的一些信息。

```shell
hwt@cxl2-2288H-V7:/sys/fs/resctrl$ tree ./info
./info
├── L2
│   ├── bit_usage
│   ├── cbm_mask # cache bit mask
│   ├── min_cbm_bits #cbm的最小连续长度
│   ├── num_closids #closid的个数
│   ├── shareable_bits 
│   └── sparse_masks
├── L3
│   ├── bit_usage
│   ├── cbm_mask
│   ├── min_cbm_bits
│   ├── num_closids
│   ├── shareable_bits
│   └── sparse_masks
├── L3_MON
│   ├── max_threshold_occupancy  # 当某rmid的llc占用量计数器低于该值时考虑释放，与rmid重用有关
│   ├── mon_features # 支持的监控事件列表
│   └── num_rmids # rmid的数量 
├── last_cmd_status  # 最后一条指令执行的结果
└── MB
    ├── bandwidth_gran # 带宽设置的粒度
    ├── delay_linear
    ├── min_bandwidth # 最小的内存带宽百分比
    ├── num_closids # closid数量
    └── thread_throttle_mode  # core上的多个thread存在不同带宽时的处理，max-以最大限制同时压制 per-thread：各自应用不同的带宽比例

4 directories, 21 files
```

![image-20240824220801623](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824220801623.png)

bandwidth_gran应该是MBA在进行带宽调控时10%的粒度修改带宽大小，min_bandwidth应该是可以调控的最小throttling value的值，delay_linear的值为1，则表示延迟尺度是线性的；如果为0，则表示延迟尺度是非线性的。

线性延迟模型假设内存访问的延迟与内存访问的频率或者数据量成正比，即增加内存访问量会导致延迟线性增加。这种模型在某些情况下可以提供较好的预测性，但在现代硬件系统中，内存访问的延迟可能受到多种因素的影响，如缓存命中率、总线争用等，这些因素可能导致延迟与访问量之间的关系并非严格的线性关系。

非线性延迟模型则考虑了这些复杂因素，能够更准确地反映在不同内存访问模式下的延迟表现。例如，在某些情况下，即使内存访问量增加，由于缓存等硬件优化机制的作用，延迟的增加可能并不显著。而在其他情况下，由于资源争用或其他瓶颈，延迟可能会有较大的跳跃或波动。

这里是可以自己设置MBA在L2 cache和L3cache之间插入延迟的比例吗？从而调整对应的控制器？

num_closids表示在内存带宽分配（Memory Bandwidth Allocation，简称MBA）中可以使用的类服务（Class of Service，简称COS）标识符的数量。这里的 "类服务" 是指不同级别的服务质量，它们允许系统管理员为不同的任务分配不同级别的内存带宽资源。

thread_throttle_mode，max：以最大限制同时压制 per-thread：各自应用不同的带宽比例。如果一个应用中的某些线程对内存带宽有更高的需求，使用 `per-thread` 模式可能会更合适。相反，如果希望避免线程间的带宽竞争，使用 `max` 模式可能会更加有效。

创建rdt_group只需在根目录下新建文件夹即可，但是rdt_group不允许嵌套，如果继续在rdt_group_demo下新建rdt_group会出现如下报错：

```shell
hwt@cxl2-2288H-V7:/sys/fs/resctrl/mon_groups$ cd mon_demo/
hwt@cxl2-2288H-V7:/sys/fs/resctrl/mon_groups/mon_demo$ ls
cpus  cpus_list  mon_data  tasks
hwt@cxl2-2288H-V7:/sys/fs/resctrl/mon_groups/mon_demo$ ls -l
total 0
-rw-r--r-- 1 root root 0  8月 24 22:32 cpus
-rw-r--r-- 1 root root 0  8月 24 22:32 cpus_list
drwxr-xr-x 4 root root 0  8月 24 22:32 mon_data
-rw-r--r-- 1 root root 0  8月 24 22:32 tasks
```

![image-20240824223404880](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824223404880.png)

![image-20240824223555335](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824223555335.png)

rdt_group设置资源分配规则可以通过修改schemata文件即可改变rdt_group的资源访问策略。MB指的是内存带宽的百分比，会受到info目录下的最小带宽比以及最小带宽粒度的限制，所有不满足最小带宽粒度的值都会被取整到满足带宽粒度。

L3表示的是LLC的掩码，7fff表示cache被划分为15份，每一个bit表示1/15，需要注意的是L3的掩码必须连续，并且满足info目录下的最小连续长度。0=和1=表示不同socket上的资源限制。

![image-20240824224031741](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824224031741.png)

为CPU绑定默认分配策略。在刚初始化rdt_group时，其下cpus和cpus_list下分别为全0和空，如下：

![image-20240824224241903](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824224241903.png)

将CPU号以掩码的方式写入cpus, 或者是以范围的方式写入cpus_list，其实二者是一样的。进入root才能写入

![image-20240824224440036](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824224440036.png)

如果cpu在移动到当前的rdt_group之前已经绑定到其他的rdt_group会自动从其他的rdt_group中的cpu对应的bit中 移出；被释放的cpu会返回到根rdt_group。并且写入后，当前rdt_group下的mon_groups目录中的监控组的cpus均被清零。

为task绑定分配策略。task被创建的那一刻会被加入根目录下的rdt_group(如下图），所有的task只能属于最多一个rdt_group，当加入一个非默认的rdt_group时会为task绑定分配策略。

![image-20240824224902937](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824224902937.png)

```shell
hwt@cxl2-2288H-V7:/sys/fs/resctrl/rdt_group_demo$ sudo -i
root@cxl2-2288H-V7:~# cd /sys/fs/resctrl/rdt_group_demo/
root@cxl2-2288H-V7:/sys/fs/resctrl/rdt_group_demo# echo 16682 > tasks 
root@cxl2-2288H-V7:/sys/fs/resctrl/rdt_group_demo# exit
logout
hwt@cxl2-2288H-V7:/sys/fs/resctrl/rdt_group_demo$ cat tasks | grep 16682
16682
# echo pid > /sys/fs/resctrl/demo_rdt_group/tasks
```

创建监控组，每个rdt_group目录下都有mon_data存放监控事件组，resctrl提供了更细化的监控组策略，可以在rdt_group的mon_groups目录下新建新的监控组。

```shell
sudo mkdir /sys/fs/resctrl/demo_rdt_group/mon_groups/demo_mon_grp
```

可以为cpu和task绑定监控组。只需要修改监控组的cpus_list和tasks文件。

```bash
echo 0-31 >  /sys/fs/resctrl/demo_rdt_group/mon_groups/demo_mon_grp/cpus_list
echo pid > /sys/fs/resctrl/demo_rdt_group/mon_groups/demo_mon_grp/tasks
```

需要注意，cpus_list必须是对应的资源组cpus_list的子集。pid同样。否则会写入失败。

## 参考：

https://www.cnblogs.com/wodemia/p/17745666.html

https://www.kernel.org/doc/html/v5.4/x86/resctrl_ui.html



![image-20240827132805257](/Users/hong/Library/Application%20Support/typora-user-images/image-20240827132805257.png)

算默认的只能创建8个res_group。



如果将一个进程的pid绑定到对应的rdt_group下，在运行中将其更换到其他的rdt_group下，进程会自动从另一个rdt_group中清除，更换到另一个rdt_group下。所以不必考虑将进程从另一个rdt_group中清除的问题。

![image-20240827134037661](/Users/hong/Library/Application%20Support/typora-user-images/image-20240827134037661.png)



cftype结构体的内容。