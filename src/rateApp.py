from pymongo import MongoClient
import numpy as np
import json
import random

db = MongoClient("localhost", 27017)['privacygrading']
rateTablePath = ("/home/lsuper/projects/privacyGradePipeline/privacyRating/data/avgCrowdSourceResult.csv")

def getRateTable(rateTablePath = rateTablePath):
    f = open(rateTablePath)
    titles = f.readline().strip().split(",")
    rateTable = {}
    for row in f.readlines():
        rateList = row.strip().split(",")
        rateTable[rateList[0]] = {titles[index]: float(rateList[index]) for index in range(1,len(rateList))}
    return rateTable

#calculate Rate for all entry in packagePair table in one loop
def calculateRate(rateTablePath = rateTablePath):
    rateDict = {}
    for entry in db.packagePair.find(timeout=False):
        packagename = entry['packagename']
        rate = calculateRateforOneApp(entry)
        rateDict[packagename] = rate
        db.packagePair.update({'packagename' : entry['packagename']}, {'$set': {'rate': rate}} )
    return rateDict

#calculate Rate for one entry each time; also return negativePermissioniPurposeDict
def calculateRateforOneApp(labeledPermissionPurposesDict, rateTable = getRateTable(rateTablePath)):
  rate = 0
  negativePermissionPurposeDict = {}
  for permissionPattern in rateTable:
      for permission, purposeSet in labeledPermissionPurposesDict.iteritems():
          if permission.find(permissionPattern) != -1:
              negativePurposeSet = set([purpose for purpose in purposeSet if rateTable[permissionPattern].get(purpose, 0) < 0])
              negativePermissionPurposeDict.update({permission: negativePermissionPurposeDict.get(permission, set()) | set(negativePurposeSet)})   
              rateList = [rateTable[permissionPattern].get(purpose, 0) for purpose in negativePurposeSet]
              rate += sum(rateList)
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

#This method transit rate to level [)
#slots and level for only minus pairs summation, max is 0; A-D
#slots = [-0.5863992984, -0.29319964921, -0.0225538192, 0.0225538192], level = ['D', 'C', 'B', 'A']

#slots and level for all pairs summation; A-F
#slots = [-4.479481834, -2.900681466, -0.7016380962, -0.3069380042, -0.0813950945, 0.0877620878, 1.159090909], level = ['F', 'E', 'D', 'C', 'B', 'A']
#slots = [-0.5863992984, -0.29319964921, -0.0225538192, 0.0225538192]
#slots = [-0.7752027885, -0.1033603718, -0.02584009295, 0.02584009295] #20140218
slots = [-0.5746956041, -0.2947156944, -0.01473578472, 0.01473578472]
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

#this method is for extractApp.extractPackagePair to use for each entry
def getLevel(rate, slots = slots, levels = levels):
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
