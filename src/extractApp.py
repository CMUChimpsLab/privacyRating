from MySQLdb import connect

from pymongo import MongoClient
from rateApp import calculateRateforOneApp, transRateToLevel, generateHistData, getLevel

dbStaticAnalysis = MongoClient("localhost", 27017)['staticAnalysis']
dbPrivacyGrading = MongoClient("localhost", 27017)['privacygrading']


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
def extractPackagePair():
    appEntry = {}
    index = 0
    labeledPackageDict = {entry['externalpack']: entry['apitype'] for entry in dbPrivacyGrading.labeled3rdparty.find({}, {'externalpack':1, 'apitype':1})}
    packagename = dbStaticAnalysis.Test_permissionlist.find().sort('filename',1)[0]['filename'].rpartition('.')[0]
    for entry in dbStaticAnalysis.Test_permissionlist.find().sort('filename',1):
        index += 1
        print index
        if packagename != entry['filename'].rpartition('.')[0]:
          packagePairEntry = {'packagename': packagename, 'pairs': {key: list(value) for key, value in appEntry.iteritems()}}
          rate = calculateRateforOneApp(packagePairEntry) 
          packagePairEntry['rate'] = rate
          packagePairEntry['level'] = getLevel(rate) 
          dbPrivacyGrading.packagePair.update({'packagename': packagename}, packagePairEntry, upsert=True)
          #reset and move to next package
          appEntry = {}
          packagename = entry['filename'].rpartition('.')[0]
        if entry['is_external'] == False:
            purpose = "INTERNAL" 
        elif entry["externalpackagename"] != "NA":
            # It is confirmed in current labeled3rdparty table, each externalpack only has one entry
            if entry['externalpackagename'] in labeledPackageDict:
                purpose = labeledPackageDict[entry['externalpackagename']]
                if purpose == "NOT EXTERNAL":
                    purpose = "INTERNAL"
            else:
                continue
        else:
            continue
        purposeSet = appEntry.get(entry["permission"], set()) | set([purpose])
        appEntry.update({entry["permission"]: purposeSet})
        print purpose, appEntry


if __name__ == "__main__":
    #copyfromMysql()
    extractPackagePair()
    transRateToLevel()
    generateHistData(200)
