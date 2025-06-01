# cgroupv2用户态使用方式

参考：

http://arthurchiao.art/blog/cgroupv2-zh/#11-%E6%9C%AF%E8%AF%AD

> [!NOTE]
>
> cgroup是control group的缩写，首字母永远不大写。
>
> cgroup作为Linux的特性或者是如"cgroup controllers"等形容词时使用；cgroups作为多个cgroup管理组使用。

## 一. cgroup基础知识

cgroup是一种以hierarchical方式组织进程的机制，在层级中以可控、可配置的方式分发系统资源。

查看当前系统中安装的cgroup版本：

```shell
grep cgroup /proc/filesystems
mount | grep cgroup
# 如果显示有cgroup2 就表示使用的是cgroup v2，一般cgroup v2 比cgroup v1 显示的挂载行更少
```

![image-20240822195736979](/Users/hong/Library/Application%20Support/typora-user-images/image-20240822195736979.png)

区分当前cgroup版本：从Debian 11, Ubuntu 22.04, RedHat 9, CentOS 9 stream开始，默认启用cgroup v2。cgroup v1中为目录结构状态的文件，而cgroup v2中以零大小的入口文件形式，并且入口文件的命名更加规范和整齐。特殊的是，在部分发行版中，启用了兼容性cgroup特性，即同时启用cgroupv1和cgroupv2，可以在/sys/fs/cgroup目录中发现一个名为`-.mount`的目录。

```shell
hwt@cxl2-2288H-V7:~$ ls -l /sys/fs/cgroup
total 0
-r--r--r--  1 root root 0  8月 22 16:54 cgroup.controllers
-rw-r--r--  1 root root 0  8月 22 16:55 cgroup.max.depth
-rw-r--r--  1 root root 0  8月 22 16:55 cgroup.max.descendants
-rw-r--r--  1 root root 0  8月 22 16:55 cgroup.pressure
-rw-r--r--  1 root root 0  8月 22 16:54 cgroup.procs
-r--r--r--  1 root root 0  8月 22 16:55 cgroup.stat
-rw-r--r--  1 root root 0  8月 22 16:54 cgroup.subtree_control
-rw-r--r--  1 root root 0  8月 22 16:55 cgroup.threads
-rw-r--r--  1 root root 0  8月 22 16:55 cpu.pressure
-r--r--r--  1 root root 0  8月 22 16:55 cpuset.cpus.effective
-r--r--r--  1 root root 0  8月 22 16:55 cpuset.cpus.isolated
-r--r--r--  1 root root 0  8月 22 16:55 cpuset.mems.effective
-r--r--r--  1 root root 0  8月 22 16:55 cpu.stat
-r--r--r--  1 root root 0  8月 22 16:55 cpu.stat.local
drwxr-xr-x  2 root root 0  8月 22 16:54 dev-hugepages.mount
drwxr-xr-x  2 root root 0  8月 22 16:54 dev-mqueue.mount
drwxr-xr-x  2 root root 0  8月 22 16:54 init.scope
-rw-r--r--  1 root root 0  8月 22 16:55 io.cost.model
-rw-r--r--  1 root root 0  8月 22 16:55 io.cost.qos
-rw-r--r--  1 root root 0  8月 22 16:55 io.pressure
-rw-r--r--  1 root root 0  8月 22 16:55 io.prio.class
-r--r--r--  1 root root 0  8月 22 16:55 io.stat
-r--r--r--  1 root root 0  8月 22 16:55 memory.numa_stat
-rw-r--r--  1 root root 0  8月 22 16:55 memory.pressure
--w-------  1 root root 0  8月 22 16:55 memory.reclaim
-r--r--r--  1 root root 0  8月 22 16:55 memory.stat
-rw-r--r--  1 root root 0  8月 22 16:55 memory.zswap.writeback
-r--r--r--  1 root root 0  8月 22 16:55 misc.capacity
-r--r--r--  1 root root 0  8月 22 16:55 misc.current
drwxr-xr-x  2 root root 0  8月 22 16:54 proc-sys-fs-binfmt_misc.mount
drwxr-xr-x  2 root root 0  8月 22 16:54 sys-fs-fuse-connections.mount
drwxr-xr-x  2 root root 0  8月 22 16:54 sys-kernel-config.mount
drwxr-xr-x  2 root root 0  8月 22 16:54 sys-kernel-debug.mount
drwxr-xr-x  2 root root 0  8月 22 16:54 sys-kernel-tracing.mount
drwxr-xr-x 56 root root 0  8月 22 22:34 system.slice
drwxr-xr-x  5 root root 0  8月 22 17:21 user.slice
```

cgroup由两部分组成：

- core:主要负责层级化组织进程；

- controllers:大部分控制器负责cgroup层级中特定类型的系统资源的分配，少部分utility控制器用于其他目的。

  - 遵循特定的结构规范(structural constraints)，可以选择性地针对一个cgroup启用或禁用某些控制器；

  -  使用lssubsys -a，将所有可用层级沿当前挂载节点列表，您就可以验证是否正确附加了层级

    ```shell
    hwt@cxl2-2288H-V7:~$ lssubsys -a
    cpuset
    cpu
    cpuacct
    blkio
    memory
    devices
    freezer
    net_cls
    perf_event
    net_prio
    hugetlb
    pids
    rdma
    misc
    ```

  - 控制器的所有行为都是hierarchical的。

    - 如果一个cgroup启用了某个控制器，那这个cgroup的sub-hierarchy中所有进程都会受控制（这里的sub-hierarchy是啥意思？这里就不太懂hierarchy和cgroup的关系了，怎么组织的？这里的sub-hiererchy就是在当前的cgroup目录下新建另一个cgroup构成的hierarchy。）
    - 如果在更接近root节点上设置了限制，下面的sub-hierarchy是无法覆盖的（为什么？不是sub-hierarchy中的所有进程都会受到控制吗？理解了，是下层的limit无法改变上上层的limit，下层limit只能进一步限制更下一层的cgroup）

**进程/线程与cgroup的关系**：

- 所有cgroup组成一个树形结构;
- 系统中的每个进程都属于且只属于某一个cgroup（但是一个cgroup中可以有很多个进程吧？是的）；
- 一个进程的所有线程属于同一个cgroup;(当前进程所有绑定在不同cores上的线程？是的，但是可以通过划分时间片来创建比2个超线程数量更多的线程)
- 创建子进程时，继承父进程的cgroup；
- 一个进程可以被迁移到其他的cgroup;
- 迁移一个进程时，**子进程不会自动跟着一起迁移(**所以这里要修改，让进程迁移时子进程也能够一起迁移；

## 二. cgroup基础操作

### 挂载(mounting)

cgroup v2只有**单个层级树(single hierarchy)**，使用如下命令挂载v2 hierarchy：

```shell
# mount -t <fstype> <device> <dir>
$ mount -t cgroup2 none $MOUNT_POINT
```

cgroupv2文件系统的**magic number**是0x63677270("cgrp")。文件系统的魔数（Magic Number）是一个特殊的数字，它**用于标识文件系统的类型**。 魔数通常存储在文件系统的超级块中，当操作系统挂载文件系统时，它会检查超级块中的魔数，以确定文件系统的类型。

控制器与v1/v2的绑定关系：

- 所有支持v2且未绑定到v1的控制器，会被自动绑定到v2 hierarchy，出现在root层级中。
- v2中未在使用的控制器，可以绑定到其他的hierarchies，即可以向后兼容混用v1和v2.

cgroupv2是单一层级树，只有一个挂载点。从cgroupv1和cgroupv2下的文件及目录形式也可以看出，cgroupv1下每种资源都拥有自己的挂载点，根据控制器类型不同，挂载到不同位置。但是cgroupv2下没有目录，所以cgroup目录本身为单一的root目录。

![image-20240822233410198](/Users/hong/Library/Application%20Support/typora-user-images/image-20240822233410198.png)

目前我们使用的系统应该是只用了cgroupv2.可以使用**`cgroup_no_v1=allows`**将cgroupv1完全禁用。

其他控制器切换相关可参考：http://arthurchiao.art/blog/cgroupv2-zh/#11-%E6%9C%AF%E8%AF%AD

### cgroupv2 mount 选项

前面 mount 命令没指定任何特殊参数。目前支持如下 mount 选项：

- `nsdelegate`：将 cgroup namespaces **（cgroupns）作为 delegation 边界**。

  系统层选项，只能在 init namespace 通过 mount/unmount 来修改这个配置。在 non-init namespace 中，这个选项会被忽略。详见下面的 [Delegation 小结](http://arthurchiao.art/blog/cgroupv2-zh/#delegation)。

- `memory_localevents`：只为当前 cgroup populate `memory.events`，**不统计任何 subtree**。

  这是 legacy 行为，如果没配置这个参数，默认行为会统计所有的 subtree。

  系统层选项，只能在 init namespace 通过 mount/unmount 来修改这个配置。在 non-init namespace 中，这个选项会被忽略。详见下面的 [Delegation 小结](http://arthurchiao.art/blog/cgroupv2-zh/#delegation)。

- `memory_recursiveprot`

  Recursively apply memory.min and memory.low protection to entire subtrees, without requiring explicit downward propagation into leaf cgroups. This allows protecting entire subtrees from one another, while retaining free competition within those subtrees. This should have been the default behavior but is a mount-option to avoid regressing setups relying on the original semantics (e.g. specifying bogusly high ‘bypass’ protection values at higher tree levels).



### 组织(organizing)进程和线程（感觉和现在的实验没啥太大关系）

##### ==进程==：创建/删除/移动/查看 cgroup

初始状态下只有root cgroup, 所有进程都属于这个cgroup。

1. 创建sub-cgroup：只需要在`/sys/fs/cgroup`下创建一个子目录

   ```shell
   mkdir $CGROUP_NAME
   ```

   - 一个cgroup可以有多个子cgroup，形成一个树形结构（所以这里的多层级应该是cgroup的多层级）；
   - 每个cgroup都有一个可读写的接口文件**cgroup.procs**:
     - 读该文件会列出这个cgroup内的所有PID，每行一个；
     - PID并未排序；
     - 同一PID可能出现多次：进程先移出再移入该cgroup，或读文件期间PID被重用了，都可能发生这种情况。

2. **将进程移动到指定cgroup:**将PID写入到相应cgroup的`cgroup.procs`文件即可。

   - 每次`write(2)`只能迁移一个进程；**write(2)是什么函数调用？是不是可以在内核中调用这个去操作将检测出拥塞的进程写入到cgroup控制组中？** man 2对应的是read/write操作，内核本身不会直接调用 `write(2)` 来操作 cgroup。内核通过系统调用接口提供服务，但具体的系统调用调用（如 `write(2)`）是由用户空间程序发起的。内核负责执行这些调用并处理相应的文件操作，包括修改 cgroup 配置。
   - 如果进程有多个线程，那将任意线程的PID写到文件，都会将该进程的所有线程迁移到相应cgroup；
   - 如果进程fork出一个子进程，那子进程属于执行fork时父进程所属的cgroup;
   - 进程退出(exit)后,  仍然留在退出时它所属的cgroup，直到这个进程**被收割（reap）**；啥叫进程被收割？在Unix和类Unix操作系统中，一个**僵尸进程**(zombie或defunct)是一个已经结束运行的进程(通过exit系统调用)，但是该进程在进程表中还占有一个进程表项： 处于终止状态。 子进程持有的进程表项包含了其退处状态，需要被父进程读取。一旦父进程(通过wait系统调用)读取到子进程的退出状态，处于僵死状态的进程表条目就会被从进程表中移除，这被称之为"reaped"。一个子进程被从进程表项移除之前，总是首先进入僵死状态。 在大多数情况下，处于僵死状态的进程能很快被他们的父进程读取到其退出状态，然后被系统收割(reap)掉 -- （相反）长时间处于僵死状态的进程通常会产生一个错误从而导致资源泄露。
   - 僵尸进程不会出现在cgroup.procs中，因此无法对僵尸进程执行cgroup迁移操作。

3. 删除cgroup/sub-cgroup

   - 如果一个cgroup已经没有任何children或活进程，直接删除对应的文件夹就删除该cgroup了；
   - 如果一个cgroup已经没有children, 虽然其中还有进程但是全是僵尸进程，那么认为这个cgroup是空的，也可以直接删除。

4. 查看进程cgroup信息: `cat /proc/$PID/cgroup`会列出该进程的cgroup membership.（应该就是这个继承下有哪些subsystem的控制组）。如果系统启用了v1,这个文件可能会包含多行，每个hierarchy, v2对应的行永远是`0::$PATH`格式：

   如果一个进程变成僵尸进程，并且与它关联的cgroup随后被删掉了，那行尾会出现deleted字样。

   ![image-20240823111500693](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823111500693.png)

   ```shell
    $ cat /proc/842/cgroup
    ...
    0::/test-cgroup/test-cgroup-nested (deleted)
   ```



## 线程

1. cgroupv2的一部分控制器支持线程粒度的资源控制，这种控制器称为threaded controllers.

   - 默认情况下，一个进程的所有线程属于同一个cgroup；
   - 线程模型使我们能将不同线程放到subtree的不同位置，而同时还能保持二者在同一资源域resource domain内。

2. 不支持线程模型的控制器称为domain controllers。将一个 cgroup 标记为 threaded，那它将作为 threaded cgroup 将加入 parent 的资源域 。而 parent 可能也是一个 threaded cgroup，它所属的资源域在 hierarchy 层级中的更 上面。一个 threaded subtree 的 root，即**第一个不是 threaded 的祖先，称为 threaded domain 或 threaded root，作为整个 subtree 的资源域。**

   在线程子树内部，进程的不同线程可以放入不同的cgroup中，并且不受内部进程约束，可以在非叶cgroup上启用线程控制器，无论非叶cgroup是否有线程。

   由于线程域 cgroup 托管子树的所有域资源消耗，因此无论其中是否有进程，它都被认为具有内部资源消耗，并且不能填充非线程化的子 cgroup。由于根 cgroup 不受内部进程约束，因此它既可以充当线程域，也可以充当域 cgroup 的父级。

   cgroup当前的操作模式或类型显示在“cgroup.type”文件中，该文件指示cgroup是普通域、作为线程子树域的域还是线程cgroup。**没找到这个文件啊？难道是现在已经没有基于线程的调控了？**找到了，不过是在kernel 5.5的版本，又可能有其他更新。

   ```shell
   # 没找到cgroup.type, 但是有cgroup.threads里面全都是cgroup控制的线程id
   # 将 cgroup 改成 threaded 模式（单向/不可逆操作）
   # cgroup 创建之后都是 domain cgroup，可以通过下面的命令将其**改成 threaded 模式**：
   $ echo threaded > cgroup.type
   # 但注意：**这个操作是单向的**，一旦设置成 threaded 模式之后，就无法再切回 domain 模式了。
   ```

   

## 进程退出通知Unpopulated Notification

每个non-root cgroup都有一个cgroup.events文件，其中包含了populated字段，描述这个cgroup的sub-hierarchy中是否存在活进程live processes.

```shell
hwt@cxl2-2288H-V7:/sys/fs/cgroup/test$ cat cgroup.events
populated 0
frozen 0
```

- 如果值是 0，表示 cgroup 及其 sub-cgroup 中没有活进程；
- 如果值是 1：那这个值变为 0 时，会**触发 poll 和 [id]notify** 事件。如果内核使用这个工具去控制进程腿出当前的cgroup可以在这两个事件的回调函数中进行一下操作？

这可以用来，例如，在一个 sub-hierarchy 内的**==所有进程退出之后触发执行清理操作==**。

The populated 状态更新和通知是递归的。以下图为例，括号中的数字表示该 cgroup 中的进程数量：

```
  A(4) - B(0) - C(1)
              \ D(0)
```

- A、B 和 C 的 `populated` 字段都应该是 `1`，而 D 的是 `0`。
- 当 C 中唯一的进程退出之后，B 和 C 的 `populated` 字段将变成 `0`，将 **在这两个 cgroup 内触发一次 cgroup.events 文件的文件修改事件**。



## 管理控制器

#### 启用和禁用

每个cgroup都有一个cgroup.controllers文件，其中列出了这个cgroup可用的所有控制器：

```shell
hwt@cxl2-2288H-V7:/sys/fs/cgroup$ cat cgroup.controllers 
cpuset cpu io memory hugetlb pids rdma misc
```

默认没有启用任何控制。启用或禁用是通过写cgroup.subtree_control文件完成的：

```shell
hwt@cxl2-2288H-V7:/sys/fs/cgroup$ cat cgroup.subtree_control 
memory pids
# 添加控制器
echo "+cpu +io" > cgroup.subtree_control
```

只有出现在cgroup.controllers中的控制器才能被启用。

- 如果像上面命令一样，一次指定多个操作，要么全部功能，要么全部失效；
- 如果对同一个控制器指定了多个操作，最后一个是有效的。

启用 cgroup 的某个控制器，意味着控制它在子节点之间分配目标资源（target resource）的行为。 考虑下面的 sub-hierarchy，括号中是已经启用的控制器：

```
  A(cpu,memory) - B(memory) - C()
                            \ D()
```

- A 启用了 `cpu` 和 `memory`，因此会控制它的 child（即 B）的 CPU 和 memory 使用；
- B 只启用了 `memory`，因此 C 和 D 的 memory 使用量会受 B 控制，但 **CPU 可以随意竞争**（compete freely）。<font color=red >**那A对cpu的限制会影响后面的C和D吗？**</font>是会有影响的。

控制器限制 children 的资源使用方式，是**创建或写入 children cgroup 的接口文件**。 还是以上面的拓扑为例：

- 在 B 上启用 `cpu` 将会在 C 和 D 的 cgroup 目录中创建 `cpu.` 开头的接口文件；
- 同理，禁用 `memory` 时会删除对应的 `memory.` 开头的文件。

![image-20240823134501140](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823134501140.png)

在root dir中查看子系统的资源限制有memory和pids资源的限制，然后查看root dir下新建的cgroup控制组test中的资源管理情况：

![image-20240823134649596](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823134649596.png)

实际上cgroup目录中所有不以cgroup.开头的控制器接口文件——在管理上都属于parent cgroup而非当前的cgroup自己。

#### 自顶向下启用控制器

资源是自顶向下分配的，只有当一个cgroup从parent获得了某种资源，才可以向下继续奋发，这意味着：

- 只有父节点用到了某个控制器，子节点才能启用；
- 对应到实现上，**所有非根节点的cgroup.subtree_control文件中，只能包含其父节点的cgroup.subtree_control中有的控制器；**
- 只要有子节点还在使用某个控制器，父节点就无法禁用该控制器

#### 将资源分给children时，parent cgroup内不能有进程(no internal process)

只有当一个 non-root cgroup 中**没有任何进程时**，才能将其 domain resource 分配给它的 children。换句话说，只有那些没有任何进程的 domain cgroup， 才能**将它们的 domain controllers 写到其 children 的 `cgroup.subtree_control` 文件中**。

这种方式保证了在给定的 domain controller 范围内，**所有进程都位于叶子节点上**， 因而**避免了 child cgroup 内的进程与 parent 内的进程竞争**的情况，便于 domain controller 扫描 hierarchy。

但<font color=red> **root cgroup 不受此限制**</font>。

- 对大部分类型的控制器来说，root 中包含了一些**没有与任何 cgroup 相关联的进程和匿名资源占用** （anonymous resource consumption），需要特殊对待。
- root cgroup 的资源占用是如何管理的，**因控制器而异**（更多信息可参考 Controllers 小结）。

注意，在 parent 的 `cgroup.subtree_control` 启用控制器之前，这些限制不会生效。 这非常重要，因为它决定了创建 populated cgroup children 的方式。 ==**要控制一个 cgroup 的资源分配**，这个 cgroup 需要（不要直接用root cgroup，创建parent cgroup和children cgroup?应该是这样的，否则无法对多种不同的资源配置进行管理，除非只有一个线程，也可以用root cgroup，但是root cgroup除了要管理用户线程还会管理一些其他的系统软件的线程，所以虽然可以实现此功能，但是从管理和维护的角度上来看不是很好，因为会影响其他默认存在于root cgroup的线程/进程的运行)：==

1. ==创建 children cgroup，==
2. ==将自己所有的进程转移到 children cgroup 中，==
3. ==在它自己的 `cgroup.subtree_control` 中启用控制器。==



## 委派Delegation

### 委派的模式

主要就是cgroup“交给谁来管理”, 即允许一个具有较高权限的用户对特定的cgroup的控制权转交给权限较低的用户或进程。主要包括以下两种方式：

- 通过授予该目录以及目录中的 `cgroup.procs`、`cgroup.threads`、`cgroup.subtree_control` 文件的写权限， 将 cgroup delegate 给一个 less privileged 用户（所以之前写失败是这个原因）；
- 如果配置了 `nsdelegate` 挂载选项，会在创建 cgroup 时自动 delegate。

对于一个给定的目录，由于其中的resource control接口文件控制着parent资源的分配，因此delegate不应该被授予写权限。

==对第二种方式，内核会拒绝除了在该 namespace 内对 `cgroup.procs`、`cgroup.subtree_control` 之外的对其他文件的写操作。==

两种委托类型的最终结果是相同的。一旦委派，用户就可以在目录下构建子层次结构，根据需要组织其中的流程，并进一步分配从父级接收的资源。所有资源控制器的限制和其他设置都是分层的，无论委托的子层次结构中发生什么，没有任何东西可以逃脱父级施加的资源限制。目前，cgroup 并未对 delegated sub-hierarchy 的 cgroup 数量或嵌套深度施加限制；但未来可能会施加显式限制。

#### Delegation Containment

委派的子层次结构是指进程不能由受委托者移入或移出子层次结构。对于权限较低的用户的委派，这是通过要求具有非 root euid 的进程满足以下条件来将其 PID 写入“cgroup.procs”文件将目标进程迁移到 cgroup 中来实现的。

- The writer must have write access to the “cgroup.procs” file.
- The writer must have write access to the “cgroup.procs” file of the common ancestor of the source and destination cgroups.

上述两个约束确保虽然委托者可以在委托子层次结构中自由迁移进程，但它不能从子层次结构外部拉入或推出到子层次结构之外。举个例子，假设cgroup C0和C1已被委托给用户U0，用户U0在C0下创建了C00、C01，在C1下创建了C10，如下所示，并且C0和C1下的所有进程都属于U0：

```
~~~~~~~~~~~~~ - C0 - C00
~ cgroup    ~      \ C01
~ hierarchy ~
~~~~~~~~~~~~~ - C1 - C10
```

假设 U0 想要将当前位于 C10 中的进程的 PID 写入“C00/cgroup.procs”。 U0 对文件有写权限；然而，源 cgroup C10 和目标 cgroup C00 的共同祖先位于委派点之上，并且 U0 对其“cgroup.procs”文件没有写访问权限，因此写入将被 -EACCES 拒绝。**（为什么C0和C1下的所有进程都属于U0，而对于源 cgroup C10 和目标 cgroup C00的cgroup.procs文件没有写权限？明白了，委派点是指将访问权交给U0的点，所以在此点无法修改）**

![image-20240823145552616](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823145552616.png)

![image-20240823145950369](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823145950369.png)

如果对subtree_control进行了修改，则只能写在root dir的cgroup.proc而不能写到叶节点的cgroup.procs中：

![image-20240823150229267](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823150229267.png)

如果没有对subtree_control进行修改，则可以在children和parent的cgroup.procs中均写入：

![image-20240823150518853](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823150518853.png)

如果没有对parent的cgroup.procs中写入控制器，即parent cgroup中没有打开对应的控制器资源，在children cgroup中也无法使用同样的控制器资源，否则会报错：

![image-20240823150737899](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823150737899.png)

参考：https://blog.csdn.net/include_IT_dog/article/details/127183601

![image-20240823151107448](/Users/hong/Library/Application%20Support/typora-user-images/image-20240823151107448.png)

1. **命名空间的隔离性**：在 Linux 中，命名空间是一种隔离机制，可以使得不同命名空间内的进程看到不同的系统视图。例如，一个进程可能只能看到其命名空间内的文件系统、网络接口等。
2. **源和目标 cgroup 的可达性**：当一个进程尝试将另一个进程从一个 cgroup 迁移到另一个 cgroup 时，内核会检查这两个 cgroup 是否都能从执行迁移操作的进程的命名空间中被访问到。
3. **迁移的约束条件**：只有当源 cgroup 和目标 cgroup 都能从该进程的命名空间中被访问时，迁移才会被允许。这是为了确保迁移操作不会违反命名空间的隔离性。
4. **迁移失败的情况**：如果源 cgroup 或目标 cgroup 不能从执行迁移操作的进程的命名空间中访问到，迁移操作将被拒绝。这种情况下，系统会返回 `-ENOENT` 错误，表示“没有这样的文件或目录”。
5. **安全性和资源控制**：这种机制确保了 cgroup 的迁移操作不会跨越命名空间的界限，从而防止了潜在的安全问题和资源泄露。
6. **实际应用**：在实际使用中，这意味着如果系统管理员想要将一个进程从一个 cgroup 迁移到另一个 cgroup，他们需要确保这两个 cgroup 都在相同的命名空间内，或者迁移操作的进程具有足够的权限来访问这两个 cgroup。

## 指导原则

#### 避免频繁在 cgroup 之间迁移进程（Organize once and control）

原则：<font color=red>创建进程前，先想好应该放在哪个 cgroup</font>；进程启动后，通过 controller 接口文件进行控制。

在 cgroup 之间迁移进程是一个**开销相对较高**的操作，而且 **有状态资源（例如 memory）**是**不会随着进程一起迁移**的。 这种行为是有意设计的，因为 there often exist inherent trade-offs between migration and various hot paths in terms of synchronization cost.

因此，**不建议为了达到某种资源限制目的而频繁地在 cgroup 之间迁移进程**。 **一个进程启动时，就应该根据系统的逻辑和资源结构分配到合适的 cgroup。** 动态调整资源分配可以通过修改接口文件来调整 controller 配置。(动态调整资源分配不是仅通过进程所属的cgroup，而是直接改进程本身所属的cgroup中的资源控制文件？最好每个进程放到一个cgroup中？是的)

#### 避免文件名冲突（Avoid Name Collisions）

cgroup 自己的接口文件和它的 children cgroup 的接口文件**位于同一目录中**， 因此创建 children cgroup 时有可能与 cgroup 自己的接口文件冲突。

- 所有 **cgroup 核心接口文件**都是以 `cgroup.` 开头，并且不会以常用的 job/service/slice/unit/workload 等作为开头或结尾。
- 每个控制器的接口文件都以 `<controller name>.` 开头，其中 `<controller> name` 由小写字母和下划线组成，但不会以 `_` 开头。

因此为避免冲突，可以用 `_` 作为前缀。

<font color=red>**cgroup 没有任何文件名冲突检测机制**，因此避免文件冲突是用户自己的责任。</font>

## 资源分配模型（Resource distribution models)

根据资源类型与使用场景的不同，cgroup控制器实现了机制不同的资源分法方式。本节主要介绍几种机制及其行为。这里的资源分配模型实际上指的是某些数值是按照权重分配，还是绝对值的最大最小值，还有资源的属性是独占还是共享这种，分配模型即资源分配的量化公式和性质。

#### Weights(资源量权重)

如cpu.weight，负责在active children之间按比例分配CPU cycle资源。这种模型中红，parent会根据所有的active children的权重来计算他们各自的占比（这个应该不是具体的一个文件吧？而是通过配置几个不同的文件来的？）。

- 由于只有那些能使用这些资源的 children 会参与到资源分配，因此这种模型 能实现资源的充分利用（work-conserving）。

- 这种分配模型本质上是动态的（the dynamic nature）, 因此常用于**无状态资源**（哪些控制器的对应的资源属于无状态资源？）。

- 权重值范围是 [1, 10000]，默认 100。这使得能以足够细的粒度增大或缩小权重

  


#### Limits

这种模型的一个例子是 io.max，负责在 IO device 上限制 cgroup 的最大 BPS 或 IOPS。

- 这种模型给 child 配置的资源使用量上限（limit）。
- 资源是**可以超分的（over-committed）**，即所有 children 的份额加起来可以大于 parent 的总可用量。
- Limits 值范围是 [0, max]，默认 max，也就是没做限制。
- 由于 limits 是可以超分的，因此所有配置组合都是合法的。

#### Protections

这种模型的一个例子是 memory.low，实现了 best-effort 内存保护（尽量满足内存的需求）。

- 在这种模型中，只要一个 cgroup 的所有祖先都处于各自的 protected level 以下，那么这个 cgroup 拿到的资源量就能达到配置值（有保障）。这里的保障可以是
  - hard guarantees
  - best effort soft boundaries
- Protection 可以超分，在这种情况下，only up to the amount available to the parent is protected among children.
- Protection 值范围是 [0, max]，默认是 0，也就是没有特别限制。
- 由于 protections 是可以超分的，因此所有配置组合都是合法的

#### Allocations

这种模型的一个**例子**是 `cpu.rt.max`，它 hard-allocates realtime slices。

- 这种模型中，cgroup 会**排他性地分配**（exclusively allocated）资源量。
- Allocation **不可超分**，即所有 children 的 allocations 之和不能超过 parent 的可用资源量。
- Allocation 值范围是 `[0, max]`，默认是 `0`，也就是不会排他性地分配资源。
- 由于 allocation 不可超分，因此某些配置可能不合法，会被拒绝；如果强制迁移进程，可能会因配置不合法（资源达到上限）而失败







cgroupv2 详解http://arthurchiao.art/blog/cgroupv2-zh/#11-%E6%9C%AF%E8%AF%AD

cfq-iosched完全公平队列调度器

Block IO层的多队列机制：https://www.bluepuni.com/archives/linux-blk-mq/

multi-queue架构分析：https://www.cnblogs.com/Linux-tech/p/12961279.html

Linux-RT带宽控制：https://blog.csdn.net/xiaoyu_750516366/article/details/134362371

https://pmem.io/ndctl/cxl/

Linux进程调度相关：https://www.cnblogs.com/LoyenWang/tag/%E8%BF%9B%E7%A8%8B%E8%B0%83%E5%BA%A6/



