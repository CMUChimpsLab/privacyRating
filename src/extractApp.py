from MySQLdb import connect
from dbConfig import dbStaticAnalysis, dbPrivacyGrading, dbAndroidApp 
from rateApp import calculateRateforOneApp, transRateToLevel, generateHistData, getLevel

import sys
import datetime

#this is deprecated.
def directFromMysql():
    if db.packagePair.count() > 0:
        print "packagePair exists"
        return

    mysqldb = connect(host="westlake.isr.cs.cmu.edu", port = 3306, user = "lsuper", passwd = "luansong", db = "appanalysisraw")

    cur1 = mysqldb.cursor()
    cur2 = mysqldb.cursor()

    cur1.execute("select * from (select packagename, permission, 3rd_party_package, is_external from test_permissionlist group by packagename, permission, 3rd_party_package, is_external) as Z;")

    appDict = {}
    for i in range(cur1.rowcount):
        row = cur1.fetchone()
        packagename, permission, third_party_package, is_external = row
        print row
        if is_external == 0:
            purpose = "INTERNAL" 
        elif third_party_package != "NA":
            cur2.execute("select apitype from labeled3rdparty where externalpack=%s", third_party_package)
            purpose = cur2.fetchone()[0]
        else:
            continue
        appEntry = appDict.get(packagename, {})
        appEntry.update({permission: appEntry.get(permission, set()) | set([purpose])})
        appDict[row[0]] = appEntry

    cur1.close()
    cur2.close()

    for key in appDict:
        db.packagePair.insert({"packagename": key, "pairs": appDict[key]})


#this is used to copy Jialiu mysql database to mongodb
#the test_permissionlist table schema names are different from Test_permissionlist
def copyfromMysql():
    if db.test_permissionlist.count() > 0:
        print "test_permissionlist exists"
        return

    if db.labeledPackageList.count() > 0:
        print "labeledPackageList exists"
        return

    mysqldb = connect(host="westlake.isr.cs.cmu.edu", port = 3306, user = "lsuper", passwd = "luansong", db = "appanalysisraw")

    cur = mysqldb.cursor()
    cur.execute("select * from test_permissionlist")
    for row in cur.fetchall():
        test_permissionEntry = {"Id": row[0], "packagename": row[1],  "appfilename": row[2],  "src": row[3], "is_external":row[4],  "3rd_party_package":row[5],  "permission":row[6],  "dest": row[7]}  
        db.test_permissionlist.insert(test_permissionEntry)
    cur.execute("select * from labeled3rdparty")
    for row in cur.fetchall():
        labeled3rdpartyEntry = {"externalpack": row[0], "website": row[1], "apitype": row[2]}
        db.labeled3rdparty.insert(labeled3rdpartyEntry)

    cur.close()

#this is used to build packagePair table
def extractPackagePair(updatedApkList):
    labeledPackageDict = {entry['externalpack']: entry['apitype'] for entry in dbPrivacyGrading.labeled3rdparty.find({}, {'externalpack':1, 'apitype':1})}
    cnt = 0
    for packagename in updatedApkList:
      cnt += 1
      print cnt
      #make sure permission in apkInfo is the version analyzed. Do not update apkInfo before extractApp.py run
      apkInfoEntry = dbAndroidApp.apkInfo.find_one({'packageName':packagename}, {'permission':1, 'updatedTimestamp':1})
      updatedTimestamp =  apkInfoEntry['updatedTimestamp']
      #if app does not require permission, it wont have a permission field in entry
      manifestPermissions =  apkInfoEntry.get('permission', [])
      manifestPermissions = [permission.lstrip('android.permission.') for permission in manifestPermissions if permission.startswith('android.permission.')]
      #for rating, will be stored in db
      labeledPermissionPurposesDict = {}
      #A whole list of permission analyzed by androguard, stored in packagePair table, externalPackage may not in labeledPackageDict and can be "NA"
      permissionExternalPackageDict = {}
      for entry in dbStaticAnalysis.Test_permissionlist.find({'packagename':packagename}):
          #if permission analyzed is not in manifest, do not add to permissionlist in packagePair
          #Note: this can be removed if all permission in Test_permissionlist are from manifest
          if entry["permission"] not in manifestPermissions:
              continue
          #update permissionExternalPackageDict
          permissionExternalPackageDict.update({entry["permission"]: permissionExternalPackageDict.get(entry["permission"], set())| set([entry['externalpackagename']])})
          #entry['is_external'] does not matter 
          if entry['externalpackagename'] == "NA":
              purpose = "INTERNAL" 
          else:
              # It is confirmed in current labeled3rdparty table, each externalpack only has one entry
              if entry['externalpackagename'] in labeledPackageDict:
                  purpose = labeledPackageDict[entry['externalpackagename']]
                  if purpose == "NOT EXTERNAL":
                      purpose = "INTERNAL"
              else:
                  continue
          purposeSet = labeledPermissionPurposesDict.get(entry["permission"], set()) | set([purpose])
          labeledPermissionPurposesDict.update({entry["permission"]: purposeSet})
               
      rate, negativePermissionPurposeDict = calculateRateforOneApp(labeledPermissionPurposesDict) 
      packagePairEntry = {'packagename': packagename, 'labeledPermissionPurposesPairs': {key: list(value) for key, value in labeledPermissionPurposesDict.iteritems()}, 'permissionExternalPackagesPairs': {key: list(value) for key, value in permissionExternalPackageDict.iteritems()}, 'negativePermissionPurposesPairs': {key: list(value) for key, value in negativePermissionPurposeDict.iteritems()}, 'manifestPermissions': manifestPermissions, 'updatedTimestamp' : updatedTimestamp}
      packagePairEntry['rate'] = rate
      
      dbPrivacyGrading.packagePair.update({'packagename': packagename}, packagePairEntry, upsert=True)
        

if __name__ == "__main__":
    updatedApkList = [] 
    if sys.argv[1] == "rebuild":
        for entry in dbAndroidApp.apkInfo.find({"isApkUpdated": False}, {"packageName":1, "isDownloaded":1}):
            if entry['isDownloaded'] == True:
                updatedApkList.append(entry["packageName"])
    else:
        updatedApkListFile = open(sys.argv[1])
        for line in updatedApkListFile:
            packagename = line.rstrip('\n')
            updatedApkList.append(packagename)
        updatedApkListFile.close()
        
    extractPackagePair(updatedApkList)
    transRateToLevel()
    now = datetime.datetime.now()
    histFileName =  "hist_" + now.strftime("%Y%m%d") + ".csv"
    outputHistogramFile = open("/home/lsuper/projects/privacyGradePipeline/privacyRating/data/hist/" + histFileName, 'w')
    generateHistData(200, outputHistogramFile)
    outputHistogramFile.close()
