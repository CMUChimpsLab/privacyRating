from pymongo import MongoClient
import numpy as np
import json
import random

db = MongoClient("localhost", 27017)['privacygrading']

def getRateTable(filename):
    f = open(filename)
    titles = f.readline().strip().split(",")
    rateTable = {}
    for row in f.readlines():
        rateList = row.strip().split(",")
        rateTable[rateList[0]] = {titles[index]: float(rateList[index]) for index in range(1,len(rateList))}
    return rateTable

def calculateRate(rateTable):
    rateDict = {}
    for entry in db.packagePair.find(timeout=False):
        if entry.has_key('rate'):
          continue
        packagename = entry['packagename']
        rate = 0
        for permissionPattern in rateTable:
            for permission, purposeList in entry['pairs'].iteritems():
                if permission.find(permissionPattern) != -1:
                    rateList = [rateTable[permissionPattern].get(purpose, 0) for purpose in purposeList if rateTable[permissionPattern].get(purpose, 0) < 0]
                    rate += sum(rateList)
        rateDict[packagename] = rate
        db.packagePair.update({'packagename' : entry['packagename']}, {'$set': {'rate': rate}} )
    return rateDict

#a utility function for generating histogram 
def generateHistData(slotSize, originalData = []):
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
    resultList.append(index)
    print slots[0], ',', 0
    for i in range(1, len(slots)):
        print slots[i], ',', resultList[i] - resultList[i-1]

#This method transit rate to level [)
#slots and level for only minus pairs summation, max is 0; A-D
#slots = [-0.5863992984, -0.29319964921, -0.0225538192, 0.0225538192], level = ['D', 'C', 'B', 'A']

#slots and level for all pairs summation; A-F
#slots = [-4.479481834, -2.900681466, -0.7016380962, -0.3069380042, -0.0813950945, 0.0877620878, 1.159090909], level = ['F', 'E', 'D', 'C', 'B', 'A']
def transRate(slots = [-0.5863992984, -0.29319964921, -0.0225538192, 0.0225538192], levels = ['D', 'C', 'B', 'A']):
    lower = min(slots) - 1
    upper = slots[0]
    for index in range(len(slots)):
        upper = slots[index]
        db.packagePair.update({'rate': {'$gte': lower, '$lt': upper}}, {'$set': {'level': levels[index]}}, multi=True)
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
    rateTable = getRateTable("../data/avgCrowdSourceResult.csv")
    rateDict = calculateRate(rateTable)
    generateHistData(200, sorted(rateDict.values()))
    #generateHistData(200)
    transRate()
    #dumpJson()
    #generateQuestions(rateTable, questionSize = 2)
