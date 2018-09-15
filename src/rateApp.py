import numpy as np
import json
import random
import pandas as pd
from dbConfig import dbPrivacyGrading

# """
# deprecated with func getRateTable
# """
# rateTablePath = ("/home/lsuper/projects/privacyGradePipeline/privacyRating/data/avgCrowdSourceResult.csv")

# def getRateTable(rateTablePath = rateTablePath):
#     """
#     deprecated function, used to get Jialiu aggregated result
#     """
#     f = open(rateTablePath)
#     titles = f.readline().strip().split(",")
#     rateTable = {}
#     for row in f.readlines():
#         rateList = row.strip().split(",")
#         rateTable[rateList[0]] = {titles[index]: float(rateList[index]) for index in range(1,len(rateList))}
#     return rateTable

# """
# use data from /home/lsuper/projects/privacyGradePrediction/data/total/ThresholdCorrectCategory/cleanResponseTotalAdjusted.csv
# calculate average score
# """
# #calculate Rate for all entry in packagePair table in one loop
# def calculateRate(rateTablePath = rateTablePath):
#     rateDict = {}
#     for entry in db.packagePair.find(timeout=False):
#         packagename = entry['packagename']
#         rate = calculateRateforOneApp(entry)
#         rateDict[packagename] = rate
#         db.packagePair.update({'packagename' : entry['packagename']}, {'$set': {'rate': rate}} )
#     return rateDict

db = dbPrivacyGrading

#calculate Rate for one entry each time; also return negativePermissioniPurposeDict
def calculateRateforOneApp(labeledPermissionPurposesDict, repoPath):
    csvPath = repoPath + "/data/total/ThresholdCorrectCategory/cleanResponseTotalAdjusted.csv"
    responseDf = pd.read_csv(csvPath, sep="\t")
    scoreDf = responseDf.groupby(["permission", "purpose"])["comfortScore"].mean().reset_index()
    rate = 0
    negativePermissionPurposeDict = {}
    for permission, purposeSet in labeledPermissionPurposesDict.iteritems():
        negativePurposeSet = set()
        for purpose in purposeSet:
            score = scoreDf[(scoreDf["permission"] == permission) & (scoreDf["purpose"] == purpose)]["comfortScore"]
            assert score.size <= 1
            if score.size == 1 and score.iloc[0] < 0:
                rate += score.iloc[0]
                negativePurposeSet.add(purpose)
        negativePermissionPurposeDict.update({permission: negativePurposeSet})
    return rate, negativePermissionPurposeDict

#a utility function for generating histogram
def generateHistData(slotSize, outputFile, originalData = []):
    slotSize = float(slotSize)
    if originalData == []:
        for entry in db.packagePair.find():
            originalData.append(entry['rate'])
    originalData = sorted(originalData)
    minData = min(originalData)
    maxData = max(originalData)
    slots = np.linspace(minData, maxData + (maxData - minData)/slotSize, slotSize + 2)
    index = 0
    resultList = []
    for slot in slots:
        while index < len(originalData):
            number = originalData[index]
            if number >= slot:
                resultList.append(index)
                break
            else:
                index += 1
    while len(resultList) < len(slots):
        resultList.append(index)
    print >> outputFile, slots[0], ',', 0
    for i in range(1, len(slots)):
        print >> outputFile, slots[i], ',', resultList[i] - resultList[i-1]

def getQuantile():
    #simple method to get slots
    originalData = []
    for entry in db.packagePair.find():
      originalData.append(entry['rate'])
    df = pd.DataFrame(originalData)
    df = df[df[0] < 0.0].reset_index(drop=True)
    slots = [df[0].quantile(0.25), df[0].quantile(0.5), df[0].quantile(0.75), df[0].quantile(1.0)]
    return slots

def updateForAPlus():
    """
    We decided to add an A+ grade on Oct. 21, 2014
    We get a list from ../data/permissionList.csv, which stored in ../data/sensitivePermissionsList
    These permissions are marked with dangerous by Google
    If an app does not request any sensitive permissions from this list, we grade it with A+

    This method will be used by transRateToLevel method
    """
    sensitivePermissionList = ["READ_USER_DICTIONARY", "READ_SMS", "WRITE_SOCIAL_STREAM", "RECEIVE_MMS", "SUBSCRIBED_FEEDS_WRITE", "WRITE_HISTORY_BOOKMARKS", "BIND_VPN_SERVICE", "CLEAR_APP_CACHE", "USE_CREDENTIALS", "KILL_BACKGROUND_PROCESSES", "PROCESS_OUTGOING_CALLS", "CHANGE_NETWORK_STATE", "READ_PROFILE", "WRITE_EXTERNAL_STORAGE", "UNINSTALL_SHORTCUT", "ADD_VOICEMAIL", "BIND_NFC_SERVICE", "BLUETOOTH_ADMIN", "CHANGE_WIFI_MULTICAST_STATE", "WRITE_CALL_LOG", "WRITE_CALENDAR", "CHANGE_WIMAX_STATE", "NFC", "WRITE_CONTACTS", "READ_CELL_BROADCASTS", "READ_PRECISE_PHONE_STATE", "READ_SOCIAL_STREAM", "USE_SIP", "READ_HISTORY_BOOKMARKS", "INSTALL_SHORTCUT", "RECEIVE_WAP_PUSH", "READ_CALENDAR", "WRITE_PROFILE", "BIND_DEVICE_ADMIN", "BLUETOOTH_STACK", "BRICK", "WRITE_SMS", "INTERNET", "CHANGE_WIFI_STATE", "AUTHENTICATE_ACCOUNTS", "BLUETOOTH", "ACCESS_MOCK_LOCATION", "READ_CONTACTS", "READ_CALL_LOG", "RECEIVE_SMS", "MANAGE_ACCOUNTS", "SYSTEM_ALERT_WINDOW", "GET_TASKS", "DISABLE_KEYGUARD", "RECORD_AUDIO", "GET_ACCOUNTS", "ACCESS_COARSE_LOCATION", "READ_PHONE_STATE", "ACCESS_FINE_LOCATION", "CALL_PHONE", "CAMERA", "SEND_SMS"]
    db.packagePair.update({"manifestPermissions": {'$nin':sensitivePermissionList}}, {'$set': {'level': "A+"}}, multi=True)

#This method transit rate to level [)
#slots and level for only minus pairs summation, max is 0; A-D
#slots = [-0.5863992984, -0.29319964921, -0.0225538192, 0.0225538192], level = ['D', 'C', 'B', 'A']

#slots and level for all pairs summation; A-F
#slots = [-4.479481834, -2.900681466, -0.7016380962, -0.3069380042, -0.0813950945, 0.0877620878, 1.159090909], level = ['F', 'E', 'D', 'C', 'B', 'A']
#slots = [-0.5863992984, -0.29319964921, -0.0225538192, 0.0225538192]
slots = [-0.7752027885, -0.1033603718, -0.02584009295, 0.02584009295] #20140218
#slots = [-0.5746956041, -0.2947156944, -0.01473578472, 0.01473578472]
#using new grading scheme, evenly split apps with negative scores
levels = ['D', 'C', 'B', 'A']
def transRateToLevel(slots = slots, levels = levels):
    lower = min(slots) - 1
    upper = slots[0]
    for index in range(len(slots)):
        upper = slots[index]
        db.packagePair.update({'rate': {'$gte': lower, '$lt': upper}}, {'$set': {'level': levels[index]}}, multi=True)
        lower = slots[index]
    db.packagePair.update({'rate': {'$gte': slots[-1]}}, {'$set': {'level': levels[-1]}}, multi=True)
    db.packagePair.update({'rate': {'$lt': slots[0]}}, {'$set': {'level': levels[0]}}, multi=True)
    #update for A+ apps
    updateForAPlus()

#this method is for extractApp.extractPackagePair to use for each entry
#Should not be used, since the slots can only be decided after rating each app, not during rating
def getLevel(rate, slots = None, levels = levels):
  if rate < slots[0]:
      return levels[0]
  if rate >= slots[-1]:
      return levels[-1]
  lower = min(slots)
  upper = slots[0]
  for index in range(len(slots)):
      upper = slots[index]
      if rate >= lower and rate < upper:
        return levels[index]
      lower = slots[index]


def dumpJson():
    lst = []
    for entry in db.packagePair.find({}, {'_id':0}):
        lst.append(entry)
    jsonFile = open('rating.json', 'w')
    jsonFile.write(json.dumps(lst, sort_keys=True, indent=2))

# this method is used for generating calibration survey questions
# level, questionSize: the number of questions for each level
def generateQuestions(rateTable, levels = ['D', 'C', 'B', 'A'], questionSize = 12):
    samples = {}
    for level in levels:
        lst = list(db.packagePair.find({'level': level}, {'_id':0}))
        samples = random.sample(lst, questionSize)
        for index in range(len(samples)):
            sample = samples[index]
            pairs = {}
            for permission, purposeList in sample['pairs'].iteritems():
                for permissionPattern in rateTable:
                    if permission.find(permissionPattern) != -1:
                       pairs[permission] = [purpose for purpose in sample['pairs'][permission] if purpose in rateTable[permissionPattern].keys()]
            sample['pairs'] = pairs
            samples[index] = sample
        jsonFile = open('survey_%s_last.json'%(level), 'w')
        jsonFile.write(json.dumps(samples, sort_keys=True, indent=2))


if __name__ == "__main__":
    #rateDict = calculateRate(rateTable)
    #generateHistData(200, sorted(rateDict.values()))
    #generateHistData(200)
    transRateToLevel()
    #dumpJson()
    #generateQuestions(rateTable, questionSize = 2)
