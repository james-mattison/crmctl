### crmctl:
_Basic tool to manage an OCF cluster_

---
####  Usage:

Example Usage:
``` bash
crmctl locate EPTT_test1
```
``` bash
crmctl failover EPTT_test1
```
``` bash
crmctl state
```

#### Commands:

#### State Overview:
&nbsp;&nbsp;&nbsp;___state___

##### Locate:

<br>  &nbsp;&nbsp;&nbsp;___locate___ _&lt;resource&gt;_
<br>  &nbsp;&nbsp;&nbsp;___locate___ _&lt;master&gt;_
<br>  &nbsp;&nbsp;&nbsp;___locate___ _&lt;slave&gt;_
  
#### Manage:

##### Ban:

<br>&nbsp;&nbsp;&nbsp;___ban___  __&lt;resource&gt;__ _[ &lt;node&gt; ]_
<br>&nbsp;&nbsp;&nbsp;___unban___  __&lt;resource&gt;__ _[ &lt;node&gt; ]_

##### Cleanup:

<br>&nbsp;&nbsp;&nbsp;___clean___  __&lt;resource&gt;__ _[ &lt;node&gt; ]_

##### Permit:

<br>&nbsp;&nbsp;&nbsp;___disable___  __&lt;resource&gt;__
<br>&nbsp;&nbsp;&nbsp;___enable___  __&lt;resource&gt;__

##### Failover:

<br>&nbsp;&nbsp;&nbsp;___failover___  __&lt;resource&gt;__
<br>&nbsp;&nbsp;&nbsp;___move___  __&lt;resource&gt;__ _[ &lt;node&gt;]_

##### Query:

#### Cluster:

<br>&nbsp;&nbsp;&nbsp;___nodes___ 
<br>&nbsp;&nbsp;&nbsp;___resources___ 
<br>&nbsp;&nbsp;&nbsp;___config___ 
<br>&nbsp;&nbsp;&nbsp;___constraints___ 
<br>&nbsp;&nbsp;&nbsp;___properties___ 

######CIB

<br>&nbsp;&nbsp;&nbsp;___read___  ___cib___

###### Misc:

<br>&nbsp;&nbsp;&nbsp;___about___
<br>&nbsp;&nbsp;&nbsp;___help___

---


