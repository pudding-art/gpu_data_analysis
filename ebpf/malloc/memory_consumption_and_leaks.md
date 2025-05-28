# 进程的内存消耗与泄漏

## 进程的虚拟地址空间VMA
进程的每一段虚拟地址空间就是一个VMA。

![vma](image-37.png)


pmap, /proc/\<pid>/maps, /proc/\<pid>/smaps

pmap是一个Linux命令行工具，用于报告进程的内存映射情况。它显示了进程的虚拟内存地址空间的布局，包括每个内存段的大小、权限、以及实际的内存使用情况。pmap对于诊断内存问题、了解进程内存布局以及优化程序性能都是非常有用的。


![pmap](image-38.png)

pmap 命令的输出包括以下几个部分：

- 地址范围：内存段的起始和结束地址。
- 大小：该内存段的大小。
- RSS：实际使用的物理内存量。
- PSS：比例共享内存量 (Proportional Set Size)，用于衡量共享内存的分配。
- 可用性：内存段的可用性和权限（如读、写、执行）。
- 路径：内存段的文件映射路径，通常为程序的共享库或内核模块路径。


maps文件可以查看某个进程的代码段、栈区、堆区、动态库、内核区对应的虚拟地址
```shell
$ cat /proc/self/maps 
00400000-0040b000 r-xp 00000000 fd:00 48              /mnt/cf/orig/root/bin/cat
0060a000-0060b000 r--p 0000a000 fd:00 48              /mnt/cf/orig/root/bin/cat
0060b000-0060c000 rw-p 0000b000 fd:00 48              /mnt/cf/orig/root/bin/cat # 代码段
0060c000-0062d000 rw-p 00000000 00:00 0               [heap] # 堆区
7f1fff43b000-7f1fff5d4000 r-xp 00000000 fd:00 861   /mnt/cf/orig/root/lib64/libc-2.15.so
7f1fff5d4000-7f1fff7d3000 ---p 00199000 fd:00 861  /mnt/cf/orig/root/lib64/libc-2.15.so
7f1fff7d3000-7f1fff7d7000 r--p 00198000 fd:00 861   /mnt/cf/orig/root/lib64/libc-2.15.so
7f1fff7d7000-7f1fff7d9000 rw-p 0019c000 fd:00 861   /mnt/cf/orig/root/lib64/libc-2.15.so
7f1fff7d9000-7f1fff7dd000 rw-p 00000000 00:00 0 
7f1fff7dd000-7f1fff7fe000 r-xp 00000000 fd:00 2554  /mnt/cf/orig/root/lib64/ld-2.15.so
7f1fff9f9000-7f1fff9fd000 rw-p 00000000 00:00 0 
7f1fff9fd000-7f1fff9fe000 r--p 00020000 fd:00 2554  /mnt/cf/orig/root/lib64/ld-2.15.so
7f1fff9fe000-7f1fff9ff000 rw-p 00021000 fd:00 2554  /mnt/cf/orig/root/lib64/ld-2.15.so
7f1fff9ff000-7f1fffa00000 rw-p 00000000 00:00 0 
7fff443de000-7fff443ff000 rw-p 00000000 00:00 0     [stack] # 用户态栈区
7fff443ff000-7fff44400000 r-xp 00000000 00:00 0     [vdso]
ffffffffff600000-ffffffffff601000 r-xp 00000000 00:00 0  [vsyscall] # 内核区
```

有时候可以通过不断查看某个进程的maps文件，通过查看其虚拟内存（堆区）是否不停增长来简单判断进程是否发生了内存溢出。<font color=#dfa>**maps文件只能显示简单的分区，smap文件可以显示每个分区的更详细的内存占用数据。**</font>下图是smaps文件内存示例, 实际显示内容会将每一个区都显示出来，下面只拷贝了栈区:

```shell
$ cat /proc/self/smaps 
7fff76e18000-7fff76e39000 rw-p 00000000 00:00 0                          [stack]
Size:                132 kB # 虚拟内存大小
KernelPageSize:        4 kB # 实际使用物理内存大小
MMUPageSize:           4 kB
Rss:                  16 kB
Pss:                  16 kB
Pss_Dirty:            16 kB
Shared_Clean:          0 kB # 页面被改，则是dirty,否则是clean,页面引用计数>1,是shared,否则是private
Shared_Dirty:          0 kB
Private_Clean:         0 kB
Private_Dirty:        16 kB
Referenced:           16 kB
Anonymous:            16 kB
KSM:                   0 kB
LazyFree:              0 kB
AnonHugePages:         0 kB
ShmemPmdMapped:        0 kB
FilePmdMapped:         0 kB
Shared_Hugetlb:        0 kB
Private_Hugetlb:       0 kB
Swap:                  0 kB # 处于交换区的页面大小
SwapPss:               0 kB # 操作系统一个页面大小
Locked:                0 kB # 体系结构MMU一个页面大小 
THPeligible:           0
VmFlags: rd wr mr mw me gd ac 
```


## VMA与程序的各个段及库

![ane](image-39.png)


smem

```shell
ong@hong-VMware-Virtual-Platform:~$ smem 
  PID User     Command                         Swap      USS      PSS      RSS 
 2374 hong     /usr/libexec/gnome-session-        0      460      511     5700 
 2311 hong     /usr/libexec/gdm-wayland-se        0      504      557     6188 
 2581 hong     /usr/libexec/gsd-screensave        0      564      613     6224 
 2283 hong     /usr/libexec/xdg-permission        0      576      625     6224 
 2566 hong     /usr/libexec/gsd-a11y-setti        0      628      689     6704 
 2835 hong     /usr/libexec/ibus-memconf          0      648      740     7112 
 3033 hong     /usr/libexec/gvfsd-metadata        0      676      754     6724 
 2909 hong     /usr/libexec/gvfs-mtp-volum        0      700      758     6740 
 2372 hong     /usr/libexec/gcr-ssh-agent         0      700      777     6628 
 2455 hong     /usr/bin/dbus-daemon --conf        0      628      802     5292 
 2580 hong     /usr/libexec/gsd-rfkill            0      760      818     6752 
 2892 hong     /usr/libexec/gvfs-goa-volum        0      704      821     6580 
 2841 hong     /usr/libexec/ibus-portal           0      744      829     7288 
 2943 hong     /usr/libexec/dconf-service         0      804      852     6184 
 2501 hong     /usr/libexec/at-spi2-regist        0      804      869     7496 
 2440 hong     /usr/libexec/at-spi-bus-lau        0      804      878     7824 
 2404 hong     /usr/libexec/gvfsd-fuse /ru        0      796      912     7276 
 2881 hong     /usr/libexec/gvfs-gphoto2-v        0      812      912     6968 
 2572 hong     /usr/libexec/gsd-housekeepi        0      876      986     7944 
 2227 hong     /usr/bin/pipewire -c filter        0      884     1037     5588 
 2390 hong     /usr/libexec/gvfsd                 0      936     1063     7936 
 2279 hong     /usr/libexec/xdg-document-p        0      956     1074     7660 
 2583 hong     /usr/libexec/gsd-smartcard         0     1040     1160     7696 
 2944 hong     /snap/snapd-desktop-integra        0      380     1184     1992 
 2937 hong     /usr/libexec/ibus-engine-si        0     1188     1297     7824 
 2584 hong     /usr/libexec/gsd-sound             0     1204     1302     9020 
 2899 hong     /usr/libexec/gvfs-afc-volum        0     1156     1366     8204 
 2838 hong     /usr/libexec/goa-identity-s        0     1364     1531     9052 
 2570 hong     /usr/libexec/gsd-datetime          0     1360     1565    11840 
 ...
```

![bar](image-40.png)

![pie](image-41.png)


## 参考文献
pmap: 命令查看 Linux 中进程的内存使用情况：
https://www.cnblogs.com/zhanchenjin/p/18404259

linux 内存查看方法：meminfo\maps\smaps\status 文件解析
https://www.cnblogs.com/jiayy/p/3458076.html

PerfGeeks团队:
https://github.com/AlexFeng123/PerfGeeks