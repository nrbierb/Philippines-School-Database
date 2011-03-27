#!/usr/bin/env python
#coding:utf-8
# Author:   --<>
# Purpose: 
# Created: 07/30/2009

import sys
import xml.dom.minidom 

data = """<instance_info name="update">
<element name="start_date"><![CDATA[std]]></element>
<element name="value"><![CDATA[----------]]></element>
</instance_info>"""

info =  xml.dom.minidom.parseString(data)
top = info.documentElement
elements = top.getElementsByTagName("element")
print top.getAttribute("name")
results = {}
for i in range(elements.length):
    element = elements.item(i)
    name = element.getAttribute("name")
    value = element.firstChild.data
    results[name] = value
    
print results   
    
