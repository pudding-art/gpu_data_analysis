CXL Fabric Management

![image-20240905143708861](/Users/hong/Library/Application%20Support/typora-user-images/image-20240905143708861.png)

CXL设备可以通过FM静态或者动态配置。FM是一个外部逻辑进程，通过FM指令请求和配置系统操作状态。

前面主要是介绍CCI Message和其format

然后介绍了CXL Switch Management

基本的switch并不需要动态配置的功能，但如果Switch想要支持MLDs或者CXL fabric拓扑则需要动态配置的功能支持。

1. 初始化配置

   涉及到Switch的非易失存储器中存储的配置设置，为了让交换机准备好进行初始化操作：

   端口配置：

   - 方向，upstream or downstream?决定了数据流向和交换机在网络拓扑中的位置
   - bandwidth，端口支持的数据传输通道数 x1, x2, x4, x8, x16等，影响端口的传输能力
   - 速率，端口支持的数据传输速率，e.g. 10Gbps, 20Gbps等，决定了端口的最大传输速度

   虚拟CXL Switch配置：

   - vPPBs数量，每个VCS支持的vPPB(virtual Physical Port Bridge, vPPB)的数量。vPPB用于连接和管理物理端口
   - 初始端口绑定配置：定义了端口如何绑定到特定的vPPBs上，这影响了数据流的路由和交换机内部的链接策略

   CCI访问设置：

   - Vendor-specific 权限设置，特定于供应商的设置，用于定义谁可以访问和管理交换机，可能包括密码，访问控制列表(ACLs)， 角色基础访问控制(RBAC)等

2. 动态配置

   CXL（Compute Express Link）交换机的动态配置，这是在初始配置完成并且交换机上的CCI（Component Command Interface）可用之后进行的。以下是对这些动态管理动作的详细解释：

   1. **查询交换机信息和配置细节**：Fabric Manager（FM）可以发送管理命令来查询CXL交换机的当前状态、配置和相关信息。这可能包括交换机的固件版本、端口状态、已绑定的vPPBs（虚拟物理端口桥）、以及其他关键的运行参数。
   2. **绑定或解绑端口**：FM可以动态地绑定或解绑交换机上的端口。绑定端口通常意味着将端口分配给特定的vPPB，以便它可以开始处理通过该端口的数据流量。解绑端口则可能是为了重新分配资源或进行维护。
   3. **注册接收和处理来自交换机的事件通知**：FM可以注册以接收交换机发出的特定事件的通知，例如：
      - **热插拔**：当新的设备被添加到网络或现有设备被移除时。
      - **意外移除**：当设备在未预期的情况下从网络中断开连接。
      - **故障**：当检测到硬件或软件故障时。
   4. **交换机端口和vPPB的管理**：当交换机的端口连接到下游的PCIe交换机，并且该端口被绑定到vPPB时，该PCIe交换机及其下游设备的管理将由VCS（虚拟CXL交换机）的主机负责，而不是由FM负责。这意味着，一旦端口被绑定，VCS的主机将接管对下游PCIe交换机及其连接的设备的管理职责，包括处理数据流量、维护连接状态和执行故障管理。

3. MLD端口管理

   对于具有MLD端口的交换机，FM需要执行以下管理活动：

   1. **MLD发现**：FM需要识别和枚举连接到CXL交换机的MLD设备。这包括确定MLD设备的存在、它们的能力以及它们支持的逻辑设备（LD）数量。
   2. **LD绑定/解绑**：FM负责将逻辑设备（LD）绑定到特定的虚拟物理端口桥（vPPB），以便它们可以参与数据流量。同样，FM也可以解绑LD，这可能在资源重新分配或维护时进行。
   3. **管理命令隧道**：FM可以通过CXL交换机的CCI隧道其管理命令到MLD设备。这意味着FM可以通过现有的CXL连接发送命令，而不需要直接连接到MLD设备。

4. MLD组件管理

   对于具有MLD端口的交换机，FM需要执行以下管理活动：

   1. **MLD发现**：FM需要识别和枚举连接到CXL交换机的MLD设备。这包括确定MLD设备的存在、它们的能力以及它们支持的逻辑设备（LD）数量。
   2. **LD绑定/解绑**：FM负责将逻辑设备（LD）绑定到特定的虚拟物理端口桥（vPPB），以便它们可以参与数据流量。同样，FM也可以解绑LD，这可能在资源重新分配或维护时进行。
   3. **管理命令隧道**：FM可以通过CXL交换机的CCI隧道其管理命令到MLD设备。这意味着FM可以通过现有的CXL连接发送命令，而不需要直接连接到MLD设备。





CCI命令包括几个重要的部分：QoS管理，动态容量分配，fabric management event records

需要实现FM吗？如果要设计成多逻辑设备，需要向上报告其LDs的数量以及Capability结构，如何管理MLD设备？查看状态等。



### CXL Fabric架构

CXL fabric架构主要作用是将CXL内存池从单点或小规模架构扩展到机架级互联以满足各领域日益增长的计算需求。Machine Learing/AI, drug discovery, agricultural and life sciences, materials science, and climate modeling.

CXL Fabric提供了一个鲁棒的路径，通过load/store内存语义或Unordered I/O(UIO)来搭建灵活、可组合的机架级系统。

CXL Fabric架构使用12-bit的PIDs(SPIDs/DPIDs)来标识多达4096个Edge Ports. 以下是为了将CXL扩展成interconnect fabric为了服务器可组合性和scale-out system的搭建的主要修改方面：

- 使用PBR和12-bit PIDs来扩展CXL fabric的规模
- 支持G-FAM设备的使用，GFD设备是一种高度扩展的内存资源，可以被所有Fabric中的主机和所有peer devices访问
- 主机和device peer通信需要使用UIO, 未来版本会提供该用例的详细说明





![image-20240905170301721](/Users/hong/Library/Application%20Support/typora-user-images/image-20240905170301721.png)

CXL Fabric包含多个Switch Edge Ports(SEPs)用来连接CXL主机的root port或CXL/PCIe Device(Dev)。FM链接到CXL Fabric，并且可能通过一个带外管理网络链接到任何选择到的终端设备上。管理网络可能是简单的2wire接口比如SMBus, I2C或I3C，或者如Ethernet一样的复杂管理网络。FM负责初始化和建立CXL Fabric以及将设备划分给不同的VHs。处理跨域流量的FM API将在未来的ECN中补充。

初始时，FM将一组设备绑定到主机的VH上，以组建系统。在主机booted之后，FM可以使用fabric的bind和unbind操作从系统中动态add或remove设备。这些系统的变化会通过fabric switches向主机发送Hot-Add和Hot-Remove events.允许由hosts和devices组成的系统动态重配置。

位于CXL Fabric上的root ports可能属于相同或不同的domains.如果root ports属于不同的domains，则不需要跨root ports去管理硬件一致性。然后如果设备支持共享，比如MLDs, MH devices,以及GFDs，可能会支持在多个域中由硬件管理cache一致性。

## CXL Fabric Use Cases

以下列举了能够从CXL Switches构成的低延迟通信的CXL Fabric获益的应用场景。

### Machine-learning Accelerators

![image-20240905172615948](/Users/hong/Library/Application%20Support/typora-user-images/image-20240905172615948.png)

用于机器学习应用的加速器可能会使用专用的CXL-switched Fabric来实现不同领域设备之间的直接通信。同样的Fabric也可以用于在加速器之间共享GFDs。每个主机和加速器都属于同一个颜色的域，这些主机和加速器在图中是直接位于彼此上方和下方的。加速器设备可以使用UIO事务来访问其他加速器和GFD的内存。在这样的系统中，每个加速器都连接到一个主机，并且在使用CXL链接时，预期与主机具有硬件缓存一致性。跨域加速器之间的通信通过**I/O一致性模型**实现。设备缓存来自另一个设备内存（HDM或PDM）的数据需要通过**软件管理的一致性**来实现，包括适当的缓存刷新和屏障。Switch Edge入口端口预计实现一个通用的地址解码器集，用于上游端口和下游端口。实现可以使用本修订版中提供的特性为加速器启用专用的CXL Fabric。然而，这并没有完全由规范定义。对等通信在第7.7.9节中进行了定义。

## HPC/Analytics Use Case

![image-20240905174533150](/Users/hong/Library/Application%20Support/typora-user-images/image-20240905174533150.png)

高性能计算和大数据分析两个领域可能从专用的CXL Fabric中受益，以实现主机之间的通信和共享G-FAM。CXL.mem或UIO可以被用来访问GFDs。一些G-FAM实现可能实现跨域硬件缓存一致性。对于共享内存的实现，仍然可以使用软件缓存一致性。主机之间的通信在第7.7.3节中有定义。

NICs可以直接将数据从网络存储移动到G-FAM设备，使用**UIO流量类别**。CXL.mem和UIO使用Fabric地址解码器将数据路由到许多领域的目标GFDs。这些功能可以帮助在高性能计算和大数据分析中实现更高效的数据传输和共享，从而提高系统性能和效率。

## Composable System

![image-20240905174622907](/Users/hong/Library/Application%20Support/typora-user-images/image-20240905174622907.png)

支持带有PBR Fabric扩展的多级交换机，为构建软件可组合系统提供了额外的能力。在图7-28中，展示了一个叶/脊柱交换机架构，其中所有资源都连接到叶子交换机。每个域可以跨越多个交换机。所有设备必须绑定到主机或FM。跨域流量仅限于CXL.mem和UIO事务。从单个叶子交换机内的资源组合系统允许实现低延迟的实现。在这种实现中，脊柱交换机仅用于跨域和G-FAM访问。这种架构可以提供更高效的系统资源利用和数据传输。

## G-FAM

GFD上的所有内存容量由动态容量（DC）机制管理，这在第8.2.9.9.9节中有定义。一个GFD允许每个请求者访问最多8个不重叠的RPID解码器，每个SPID的最大解码器数量取决于具体实现。每个解码器都有一个从HPA空间到常见DPA空间的转换，一个指示缓存一致性是由软件还是硬件维护的标志，以及有关多个GFD交错的信息（如果使用的话）。对于每个请求者，FM可以在DPA空间中定义DC区域，并通过GAE将此信息传达给主机。预期主机将为其域中的所有RPID编程**Fabric地址段表（FAST）解码器和GFD解码器**，以映射主机或其关联加速器需要访问的每个DC区域的整个DPA范围。

G-FAM内存范围可以跨越从2到256个GFD的任何二的幂次方数目，其中交错粒度为256B、512B、1 KB、2 KB、4 KB、8 KB或16 KB。任何位于CXL Fabric中的GFD，如第2.7节中所定义，都可以用于向交错集合贡献内存。

如果一个GFD支持UIO Direct P2P到HDM（见第7.7.9.1节），所有GFD端口都应支持UIO，并且对于每个GFD链路，其链路伙伴也支持UIO，则端口应自动启用VC3（见第7.7.11.5.1节）。



HDM（Host-attached Device Memory）被操作系统/VMM视为普通内存。然而，与主机连接的内存相比，HDM可能具有不同的性能/延迟属性。因此，具有CXL.mem设备的系统可以被视为异构内存系统。ACPI HMAT被引入用于这种系统，并可以报告与不同内存范围相关的内存延迟和带宽特性。 ACPI规范版本6.2及更高版本包含了HMAT的修订版1的定义。截至2018年8月，ACPI工作组决定废弃HMAT的修订版1，因为它存在一些缺陷。因此，随后的讨论涉及HMAT的修订版2。此外，ACPI引入了一种称为通用亲和性（GI）结构的新类型亲和性结构。GI结构适用于描述不是处理器的执行引擎，如加速器。支持CXL.mem的加速器将导致两个SRAT条目 - 一个GI条目表示加速器核心，一个内存条目表示连接的HDM。当描述CXL.cache加速器时，GI条目尤其有用。在引入GI之前，CXL.cache加速器无法在SRAT/HMAT中描述为一个独立实体，而必须与连接的CPU结合。通过这个规范变更，CXL.cache加速器可以被描述为一个独立的亲和性域。_PXM方法可用于识别与PCI设备关联的亲和性域。由于传统操作系统不理解GI，因此在运行此类操作系统，系统固件需要返回与I/O设备最密切关联的处理器域。ASL代码可以使用Platform-Wide _OSC Capabilities DWORD 2的第17位来检测操作系统是否支持GI。

在具有CXL.cache设备和CXL.mem设备的系统中，系统固件必须构建并向操作系统报告SRAT和HMAT。由于系统固件不了解HDM的属性，该信息必须以CDAT的形式从CXL设备中获取。设备可以通过**Table Access DOE或通过UEFI驱动程序导出CDAT**。系统固件将其对主机和CXL连接的信息与在构建SRAT和HMAT期间从各种CXL组件获取的CDAT内容相结合。



CXL内存设备提供易失性内存（如DRAM）时，每次系统引导时可能会暴露不同的交错几何结构。这可能是由于其他设备的添加或移除，或者平台默认交错策略的更改导致的。对于易失性内存，这些交错的变化通常不会影响主机软件，因为通常不会期望易失性内存内容在重启后得到保留。然而，对于持久内存，确切地保留交错几何结构是至关重要的，以便每次系统引导时以相同的方式向主机软件呈现持久内存内容。

类似于交错配置，持久内存设备可能被分区为命名空间，这些命名空间定义了持久内存的卷。这些命名空间必须在每次系统引导时以相同的方式重新组装，以防止数据丢失。第8.2.9节定义了用于读取和写入CXL内存设备的标签存储区域（LSA）的邮箱操作：获取LSA和设置LSA。此外，识别内存设备邮箱命令公开了给定CXL内存设备的LSA的大小。LSA允许将交错和命名空间配置细节持久地存储在所有涉及的设备上，以便如果将设备移至不同的插槽或机器，则配置数据“跟随设备”。LSA的使用类似于磁盘RAID阵列将配置信息写入到阵列中每个磁盘的保留区域，以便在配置更改时保留几何结构。

CXL内存设备可以为多个持久性内存交错集做出贡献，受限于交错资源，如HDM解码器或其他平台资源。每个持久性内存交错集可以被分区为多个命名空间，受限于资源，如标签存储空间和支持的平台配置。

LSA的格式以及更新和解释LSA的规则在本节中有规定。CXL内存设备不直接解释LSA，它们只提供存储域和用于访问的邮箱命令。配置交错集和命名空间的软件，如预启动固件或主机操作系统，应遵循LSA的规则。



















