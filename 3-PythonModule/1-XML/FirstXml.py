import xml.etree.ElementTree as ET
tree = ET.parse("F:\\0_PYTHON\\3-PythonModule\\1-XML\\example.xml")
root = tree.getroot()
# print(root.tag)
# for t in root:
#     print(t.tag)
#     print(t.attrib)
#     for tt in t:
#         print(tt.tag)
#         print(tt.attrib)

for n in root.iter('gdppc'):
    print(n.tag, n.attrib)
