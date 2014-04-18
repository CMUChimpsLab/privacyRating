"""
This script is used to extract Android Permission and its description and dangerous level from Android source code manifest.xml and string.xml.
The permission list is used to us to generate a sensitive permission list
"""
import xml.etree.ElementTree as ET
import re

manifestFilePath = "../data/base-master-core-res/AndroidManifest.xml"
descriptionFilePath = "../data/base-master-core-res-res-values/strings.xml"
outputFile = open("../data/permissionList.csv", "w")

manifestTree = ET.parse(manifestFilePath)
descriptionTree = ET.parse(descriptionFilePath)

schemaStr = "{http://schemas.android.com/apk/res/android}"
permissionList = []

for permission in manifestTree.findall("permission"):
    """
    label is A name for the permission, one that can be displayed to users. E.g. Send SMS messages   
    name is Java style name. E.g. android.permission.SEND_SMS
    """
    permissionList.append({"label": permission.get(schemaStr + "label")[8:] if permission.get(schemaStr + "label") else "", "name": permission.get(schemaStr + "name", ""), "description": permission.get(schemaStr + "description")[8:] if permission.get(schemaStr + "description") else "", "permissionFlags": permission.get(schemaStr + "permissionFlags", ""), "permissionGroup": permission.get(schemaStr + "permissionGroup", ""), "protectionLevel": permission.get(schemaStr + "protectionLevel", "")})

for p in permissionList:
    if p["description"] != "":
        print p
        p["description"] = descriptionTree.findall(".//*[@name=%s]"%("\""+ p["description"]+ "\""))[0].text.replace("\n","")
        p["description"] = re.sub(" +", " ", p["description"])
        p["label"] = descriptionTree.findall(".//*[@name=%s]"%("\""+ p["label"]+ "\""))[0].text.replace("\n","")

print >> outputFile, "\t".join(sorted(p.keys()))
for p in permissionList:
    print >> outputFile, "\t".join([p[entry] for entry in sorted(p.keys())])

outputFile.close()
